# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from transport_management.location_master import validate_active_transport_locations
from transport_management.truck_master import validate_owned_truck_available

ACTIVE_OPERATIONAL_STATUSES = {"ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED"}
TERMINAL_STATUSES = {"CLOSED", "CANCELLED"}
STATUS_SEQUENCE = ("PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED")
ALLOWED_FORWARD_TRANSITIONS = dict(zip(STATUS_SEQUENCE, STATUS_SEQUENCE[1:]))
ALLOWED_STATUSES = set(STATUS_SEQUENCE) | {"CANCELLED", "EXCEPTION"}
ALLOWED_EXECUTION_SOURCES = {"OWN", "HIRED"}


class TransportTrip(Document):
	def before_validate(self):
		if not self.status:
			self.status = "PLANNED"

		if not self.execution_source:
			self.execution_source = "OWN"

		if self.status == "POD_RECEIVED" and self.pod_attachment and not self.pod_received_at:
			self.pod_received_at = now_datetime()

	def validate(self):
		self.validate_transport_job_exists()
		self.validate_execution_source()
		self.validate_quantities()
		self.validate_locations()
		self.validate_status_transition()
		self.validate_pod()
		self.validate_reserved_quantity()

	def validate_transport_job_exists(self):
		if not self.transport_job or not frappe.db.exists("Transport Job", self.transport_job):
			frappe.throw(_("Transport Job must exist."))

	def validate_execution_source(self):
		if self.execution_source not in ALLOWED_EXECUTION_SOURCES:
			frappe.throw(_("Invalid Execution Source {0}.").format(self.execution_source))

		if self.execution_source == "OWN":
			validate_owned_truck_available(self.vehicle)
			if not self.driver:
				frappe.throw(_("Driver is required for own fleet Transport Trips."))
			return

		self.validate_hired_execution()

	def validate_hired_execution(self):
		if not self.transporter:
			frappe.throw(_("Transporter is required for hired Transport Trips."))
		if not self.hired_vehicle:
			frappe.throw(_("Hired Vehicle is required for hired Transport Trips."))

		transporter = frappe.db.get_value(
			"Supplier",
			self.transporter,
			["is_transporter", "transporter_status", "disabled"],
			as_dict=True,
		)
		if not transporter:
			frappe.throw(_("Transporter Supplier must exist."))
		if not transporter.is_transporter:
			frappe.throw(_("Selected Supplier must be marked as a Transporter."))
		if transporter.disabled:
			frappe.throw(_("Disabled Suppliers cannot be used as Transporters."))
		if transporter.transporter_status != "Active":
			frappe.throw(_("Transporter Status must be Active."))

		hired_vehicle = frappe.db.get_value(
			"Hired Vehicle",
			self.hired_vehicle,
			["transporter", "active"],
			as_dict=True,
		)
		if not hired_vehicle:
			frappe.throw(_("Hired Vehicle must exist."))
		if hired_vehicle.transporter != self.transporter:
			frappe.throw(_("Hired Vehicle must belong to the selected Transporter."))
		if not hired_vehicle.active:
			frappe.throw(_("Inactive Hired Vehicles cannot be used on Transport Trips."))

	def validate_quantities(self):
		planned_quantity = flt(self.planned_quantity)
		if not isfinite(planned_quantity) or planned_quantity <= 0:
			frappe.throw(_("Planned Quantity must be greater than zero."))

		if self.actual_quantity is not None and self.actual_quantity != "":
			actual_quantity = flt(self.actual_quantity)
			if not isfinite(actual_quantity) or actual_quantity < 0:
				frappe.throw(_("Actual Quantity cannot be negative."))

	def validate_locations(self):
		if self.loading_site and self.loading_site == self.unloading_site:
			frappe.throw(_("Loading Site and Unloading Site must be different."))

		validate_active_transport_locations(
			self,
			(("loading_site", _("Loading Site")), ("unloading_site", _("Unloading Site"))),
		)

	def validate_status_transition(self):
		if self.status not in ALLOWED_STATUSES:
			frappe.throw(_("Invalid Transport Trip status {0}.").format(self.status))

		if self.is_new():
			if self.status != "PLANNED":
				frappe.throw(_("New Transport Trips must start as PLANNED."))
			return

		previous_status = frappe.db.get_value(self.doctype, self.name, "status")
		if previous_status == self.status:
			return

		if previous_status == "CLOSED":
			frappe.throw(_("Closed Transport Trips cannot be reopened or changed."))

		if self.status == "CANCELLED":
			if previous_status == "CLOSED":
				frappe.throw(_("Closed Transport Trips cannot be cancelled."))
			return

		if self.status == "EXCEPTION":
			if previous_status in ACTIVE_OPERATIONAL_STATUSES:
				return
			frappe.throw(_("EXCEPTION is only allowed from active Transport Trip statuses."))

		expected_next_status = ALLOWED_FORWARD_TRANSITIONS.get(previous_status)
		if self.status != expected_next_status:
			frappe.throw(
				_("Invalid Transport Trip status transition from {0} to {1}.").format(
					previous_status, self.status
				)
			)

	def validate_pod(self):
		if self.status == "POD_RECEIVED" and not self.pod_attachment:
			frappe.throw(_("POD Attachment is required before setting status to POD_RECEIVED."))

		if self.status == "CLOSED":
			previous_status = None if self.is_new() else frappe.db.get_value(self.doctype, self.name, "status")
			if previous_status != "POD_RECEIVED":
				frappe.throw(_("Transport Trip must pass POD_RECEIVED before it can be CLOSED."))
			if not self.pod_attachment:
				frappe.throw(_("POD Attachment is required before closing a Transport Trip."))

	def validate_reserved_quantity(self):
		if self.status == "CANCELLED":
			return

		job = lock_transport_job(self.transport_job)
		requested_quantity = flt(job.requested_quantity, 6)
		already_planned = flt(get_reserved_quantity(self.transport_job, exclude_name=self.name), 6)
		attempted_quantity = flt(self.planned_quantity, 6)
		remaining_quantity = flt(requested_quantity - already_planned, 6)

		if attempted_quantity > remaining_quantity:
			frappe.throw(
				_(
					"Transport Trip planned quantity exceeds the Transport Job requested quantity.<br>"
					"Requested Quantity: {0}<br>Already Planned: {1}<br>"
					"Remaining Quantity: {2}<br>Attempted Quantity: {3}"
				).format(requested_quantity, already_planned, remaining_quantity, attempted_quantity)
			)


@frappe.whitelist()
def get_defaults_from_transport_job(transport_job):
	if not transport_job:
		frappe.throw(_("Transport Job is required."))
	job = frappe.get_doc("Transport Job", transport_job)
	return {
		"transport_job": job.name,
		"trip_date": job.requested_date,
		"loading_site": job.loading_site,
		"unloading_site": job.unloading_site,
		"material": job.material,
		"uom": job.uom,
	}


def lock_transport_job(transport_job):
	rows = frappe.db.sql(
		"""
		select name, requested_quantity
		from `tabTransport Job`
		where name = %s
		for update
		""",
		transport_job,
		as_dict=True,
	)
	if not rows:
		frappe.throw(_("Transport Job must exist."))
	return rows[0]


def get_reserved_quantity(transport_job, exclude_name=None):
	filters = ["transport_job = %s", "status != 'CANCELLED'"]
	values = [transport_job]
	if exclude_name:
		filters.append("name != %s")
		values.append(exclude_name)

	reserved = frappe.db.sql(
		f"""
		select coalesce(sum(planned_quantity), 0)
		from `tabTransport Trip`
		where {' and '.join(filters)}
		""",
		values,
	)[0][0]
	return flt(reserved, 6)
