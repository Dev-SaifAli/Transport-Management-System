# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, today

from transport_management.cargo_type_master import (
	get_effective_material,
	validate_material_allows_hired_vehicle,
	validate_material_allows_owned_truck,
)
from transport_management.location_master import validate_transport_location_usage
from transport_management.transport_management.doctype.transport_charge_rule.transport_charge_rule import (
	apply_transport_trip_charges,
	sync_legacy_charge_totals,
)
from transport_management.transport_management.doctype.transport_job.transport_job import refresh_quantity_progress
from transport_management.truck_master import validate_owned_truck_available

ACTIVE_OPERATIONAL_STATUSES = {"ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED"}
VEHICLE_RESERVED_STATUSES = {"PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT"}
TERMINAL_STATUSES = {"CLOSED", "CANCELLED"}
STATUS_SEQUENCE = ("PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED")
ALLOWED_FORWARD_TRANSITIONS = dict(zip(STATUS_SEQUENCE, STATUS_SEQUENCE[1:]))
ALLOWED_STATUSES = set(STATUS_SEQUENCE) | {"CANCELLED", "EXCEPTION"}
ALLOWED_EXECUTION_SOURCES = {"OWN", "HIRED"}
TON_UOM = "TON"


class TransportTrip(Document):
	def before_validate(self):
		if not self.status:
			self.status = "PLANNED"

		if not self.execution_source:
			self.execution_source = "OWN"

		if not self.trip_date:
			self.trip_date = today()

		if not self.uom:
			self.uom = TON_UOM

		if self.status == "POD_RECEIVED" and self.pod_attachment and not self.pod_received_at:
			self.pod_received_at = now_datetime()

		if self.status in {"LOADED", "IN_TRANSIT"} and self.loaded_quantity and not self.loading_datetime:
			self.loading_datetime = now_datetime()

		if self.status in {"DELIVERED", "POD_RECEIVED", "CLOSED"} and self.delivered_quantity and not self.delivery_datetime:
			self.delivery_datetime = now_datetime()

	def validate(self):
		self.validate_transport_job_exists()
		self.validate_transport_job_has_remaining_quantity()
		self.validate_execution_source()
		self.validate_quantities()
		self.validate_material_matches_transport_job()
		self.validate_locations()
		self.validate_status_transition()
		self.validate_pod()
		self.validate_reserved_quantity()
		sync_legacy_charge_totals(self)

	def on_update(self):
		refresh_quantity_progress(self.transport_job)

	def on_trash(self):
		refresh_quantity_progress(self.transport_job)

	def validate_transport_job_exists(self):
		if not self.transport_job or not frappe.db.exists("Transport Job", self.transport_job):
			frappe.throw(_("Transport Job must exist."))

	def validate_transport_job_has_remaining_quantity(self):
		if not self.is_new() or self.status == "CANCELLED":
			return
		if flt(frappe.db.get_value("Transport Job", self.transport_job, "remaining_quantity"), 6) <= 0:
			frappe.throw(_("This Transport Job is fully delivered. No remaining quantity is available for a new Trip."))

	def validate_execution_source(self):
		if self.execution_source not in ALLOWED_EXECUTION_SOURCES:
			frappe.throw(_("Invalid Execution Source {0}.").format(self.execution_source))

		if self.execution_source == "OWN":
			self.validate_vehicle_not_reserved()
			validate_owned_truck_available(self.vehicle)
			self.validate_owned_truck_material_compatibility()
			if not self.driver:
				frappe.throw(_("Driver is required for own fleet Transport Trips."))
			return

		self.validate_hired_execution()

	def validate_owned_truck_material_compatibility(self):
		if not self.should_validate_owned_truck_material_compatibility():
			return
		validate_material_allows_owned_truck(self.get_effective_material(), self.vehicle)

	def should_validate_owned_truck_material_compatibility(self):
		if self.execution_source != "OWN" or not self.vehicle:
			return False
		if self.is_new():
			return True
		return any(
			self.has_value_changed(fieldname)
			for fieldname in ("vehicle", "material", "transport_job", "execution_source")
		)

	def get_effective_material(self):
		return get_effective_material(self.material, self.transport_job)

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
		self.validate_hired_vehicle_material_compatibility()

	def validate_hired_vehicle_material_compatibility(self):
		if not self.should_validate_hired_vehicle_material_compatibility():
			return
		validate_material_allows_hired_vehicle(
			self.get_effective_material(),
			self.hired_vehicle,
			self.transporter,
		)

	def should_validate_hired_vehicle_material_compatibility(self):
		if self.execution_source != "HIRED" or not self.hired_vehicle:
			return False
		if self.is_new():
			return True
		return any(
			self.has_value_changed(fieldname)
			for fieldname in (
				"hired_vehicle",
				"transporter",
				"material",
				"transport_job",
				"execution_source",
			)
		)

	def validate_quantities(self):
		planned_quantity = flt(self.planned_quantity)
		if not isfinite(planned_quantity) or planned_quantity <= 0:
			frappe.throw(_("Planned Quantity must be greater than zero."))

		if self.uom != TON_UOM:
			frappe.throw(_("Transport Trip UOM must be TON."))

		if self.actual_quantity is not None and self.actual_quantity != "":
			actual_quantity = flt(self.actual_quantity)
			if not isfinite(actual_quantity) or actual_quantity < 0:
				frappe.throw(_("Actual Quantity cannot be negative."))

		loaded_quantity = self.get_optional_quantity("loaded_quantity", _("Loaded Quantity"))
		delivered_quantity = self.get_optional_quantity("delivered_quantity", _("Delivered Quantity"))

		if self.status in {"LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"} and not loaded_quantity:
			frappe.throw(_("Enter Loaded Quantity before marking this trip as Loaded."))
		if self.status in {"DELIVERED", "POD_RECEIVED", "CLOSED"} and not delivered_quantity:
			frappe.throw(_("Delivered Quantity is required when Transport Trip is DELIVERED."))
		if self.status in {"LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"} and not self.loading_datetime:
			frappe.throw(_("Loading Date/Time is required when Transport Trip is LOADED."))
		if self.status in {"DELIVERED", "POD_RECEIVED", "CLOSED"} and not self.delivery_datetime:
			frappe.throw(_("Delivery Date/Time is required when Transport Trip is DELIVERED."))
		if loaded_quantity and delivered_quantity and delivered_quantity > loaded_quantity:
			frappe.throw(_("Delivered Quantity cannot exceed Loaded Quantity."))
		self.validate_vehicle_capacity(planned_quantity, loaded_quantity)

	def get_optional_quantity(self, fieldname, label):
		value = self.get(fieldname)
		if value is None or value == "":
			return 0
		quantity = flt(value, 6)
		if not isfinite(quantity) or quantity < 0:
			frappe.throw(_("{0} cannot be negative.").format(label))
		return quantity

	def validate_vehicle_capacity(self, planned_quantity, loaded_quantity):
		if self.execution_source != "OWN" or not self.vehicle:
			return
		truck = frappe.db.get_value("Truck", self.vehicle, ["capacity", "capacity_uom"], as_dict=True)
		if not truck or not flt(truck.capacity):
			return
		if truck.capacity_uom and truck.capacity_uom != TON_UOM:
			return
		capacity = flt(truck.capacity, 6)
		if planned_quantity > capacity:
			frappe.throw(_("Planned Quantity cannot exceed Vehicle capacity {0} TON.").format(capacity))
		if loaded_quantity and loaded_quantity > capacity:
			frappe.throw(_("Loaded Quantity cannot exceed Vehicle capacity {0} TON.").format(capacity))

	def validate_vehicle_not_reserved(self):
		if not self.vehicle or self.status not in VEHICLE_RESERVED_STATUSES:
			return
		existing_trip = get_active_vehicle_trip(self.vehicle, exclude_name=self.name)
		if not existing_trip:
			return
		frappe.throw(
			_("Vehicle {0} is already assigned to active Trip {1}. Please select another available vehicle.").format(
				self.vehicle,
				existing_trip,
			)
		)

	def validate_material_matches_transport_job(self):
		get_effective_material(self.material, self.transport_job, validate_mismatch=True)

	def validate_locations(self):
		if self.loading_site and self.loading_site == self.unloading_site:
			frappe.throw(_("Loading Site and Unloading Site must be different."))

		validate_transport_location_usage(self.loading_site, {"Loading", "Both"}, _("Loading Location"))
		validate_transport_location_usage(self.unloading_site, {"Unloading", "Both"}, _("Unloading Location"))

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
	if flt(job.remaining_quantity, 6) <= 0:
		frappe.throw(_("This Transport Job is fully delivered. No remaining quantity is available for a new Trip."))
	return {
		"transport_job": job.name,
		"trip_date": job.requested_date,
		"loading_site": job.loading_site,
		"unloading_site": job.unloading_site,
		"material": job.material,
		"uom": TON_UOM,
	}


@frappe.whitelist()
def transition_trip_status(transport_trip, status):
	if not transport_trip:
		frappe.throw(_("Transport Trip is required."))
	if status not in ALLOWED_STATUSES:
		frappe.throw(_("Invalid Transport Trip status {0}.").format(status))

	trip = frappe.get_doc("Transport Trip", transport_trip)
	trip.status = status
	trip.save()
	return {
		"name": trip.name,
		"status": trip.status,
	}


@frappe.whitelist()
def calculate_charges(transport_trip):
	if not transport_trip:
		frappe.throw(_("Transport Trip is required."))
	return apply_transport_trip_charges(transport_trip)


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


def get_active_vehicle_trip(vehicle, exclude_name=None):
	filters = ["vehicle = %s", "execution_source = 'OWN'", "status in %s"]
	sql_values = [vehicle]
	sql_values.append(tuple(VEHICLE_RESERVED_STATUSES))
	if exclude_name:
		filters.append("name != %s")
		sql_values.append(exclude_name)

	rows = frappe.db.sql(
		f"""
		select name
		from `tabTransport Trip`
		where {' and '.join(filters)}
		order by creation asc
		limit 1
		for update
		""",
		tuple(sql_values),
		as_dict=True,
	)
	return rows[0].name if rows else None
