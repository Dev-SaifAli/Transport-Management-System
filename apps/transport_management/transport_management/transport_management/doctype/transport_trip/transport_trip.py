# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, today

from transport_management.cargo_type_master import (
	get_effective_material,
	validate_material_allows_hired_vehicle,
	validate_material_allows_owned_truck,
)
from transport_management.loading_stops import (
	copy_loading_stops,
	get_scaled_stop_quantities,
	sync_primary_loading_from_stops,
	validate_loading_stop_rows,
)
from transport_management.location_master import validate_transport_location_usage
from transport_management.transport_management.doctype.transport_charge_rule.transport_charge_rule import (
	apply_transport_trip_charges,
	sync_legacy_charge_totals,
)
from transport_management.transport_management.doctype.transport_job.transport_job import (
	OPEN_QUANTITY_MODE,
	refresh_quantity_progress,
)
from transport_management.truck_master import validate_owned_truck_available

ACTIVE_OPERATIONAL_STATUSES = {"ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED"}
VEHICLE_RESERVED_STATUSES = {"PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "EXCEPTION"}
TERMINAL_STATUSES = {"CLOSED", "CANCELLED"}
STATUS_SEQUENCE = ("PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED")
ALLOWED_FORWARD_TRANSITIONS = dict(zip(STATUS_SEQUENCE, STATUS_SEQUENCE[1:]))
ALLOWED_STATUSES = set(STATUS_SEQUENCE) | {"CANCELLED", "EXCEPTION"}
ALLOWED_EXECUTION_SOURCES = {"OWN", "HIRED"}
TRIP_DISPATCH_ROLES = {"TMS Trip Data Entry", "TMS + Expense Data Entry", "Transport Manager", "Transport Admin", "System Manager"}
TRIP_RESOURCE_ACTIVE_STATUSES = tuple(sorted(VEHICLE_RESERVED_STATUSES))
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
		if not self.commercial_rate_status:
			job_mode = frappe.db.get_value("Transport Job", self.transport_job, "quantity_mode")
			self.commercial_rate_status = "PENDING_CONFIRMATION" if job_mode == OPEN_QUANTITY_MODE else "NOT_APPLICABLE"

		if not self.is_open_quantity_job():
			self.set_loading_stops_from_job_if_missing()
			self.scale_job_loading_stops_to_trip_quantity()
			sync_primary_loading_from_stops(self, "loading_site")

		if self.status == "POD_RECEIVED" and self.pod_attachment and not self.pod_received_at:
			self.pod_received_at = now_datetime()

		if self.status in {"LOADED", "IN_TRANSIT"} and self.loaded_quantity and not self.loading_datetime:
			self.loading_datetime = now_datetime()

		if self.status in {"DELIVERED", "POD_RECEIVED", "CLOSED"} and self.delivered_quantity and not self.delivery_datetime:
			self.delivery_datetime = now_datetime()

	def validate(self):
		self.validate_transport_job_exists()
		self.validate_transport_job_has_remaining_quantity()
		self.validate_status_transition()
		self.validate_execution_source()
		self.validate_quantities()
		self.validate_material_matches_transport_job()
		self.validate_locations()
		self.validate_planned_loading_point()
		self.validate_protected_loading_and_rate_fields()
		self.validate_verified_delivery()
		self.validate_open_loading_confirmation()
		self.validate_pod()
		self.validate_reserved_quantity()
		sync_legacy_charge_totals(self)

	def before_save(self):
		self.set_driver_assignment_notification_flags()

	def on_update(self):
		refresh_quantity_progress(self.transport_job)
		self.enqueue_driver_assignment_notification()

	def on_trash(self):
		refresh_quantity_progress(self.transport_job)

	def set_driver_assignment_notification_flags(self):
		self.flags.previous_driver = None
		self.flags.notify_assigned_driver = False

		if not self.driver:
			return

		if self.is_new():
			self.flags.notify_assigned_driver = True
			return

		previous_driver = frappe.db.get_value(self.doctype, self.name, "driver")
		self.flags.previous_driver = previous_driver
		self.flags.notify_assigned_driver = bool(previous_driver != self.driver)

	def enqueue_driver_assignment_notification(self):
		if not self.flags.notify_assigned_driver:
			return

		from transport_management.services.driver_notifications import (
			queue_driver_trip_assignment_notification,
		)

		queue_driver_trip_assignment_notification(self.name, self.flags.previous_driver)

	def validate_transport_job_exists(self):
		if not self.transport_job or not frappe.db.exists("Transport Job", self.transport_job):
			frappe.throw(_("Transport Job must exist."))

	def validate_transport_job_has_remaining_quantity(self):
		if not self.is_new() or self.status == "CANCELLED":
			return
		job = frappe.db.get_value(
			"Transport Job",
			self.transport_job,
			["quantity_mode", "remaining_quantity"],
			as_dict=True,
		)
		if job.quantity_mode == OPEN_QUANTITY_MODE:
			return
		if flt(job.remaining_quantity, 6) <= 0:
			frappe.throw(_("This Transport Job is fully delivered. No remaining quantity is available for a new Trip."))

	def validate_execution_source(self):
		if self.execution_source not in ALLOWED_EXECUTION_SOURCES:
			frappe.throw(_("Invalid Execution Source {0}.").format(self.execution_source))

		if self.execution_source == "OWN":
			self.validate_assignment_availability()
			validate_owned_truck_available(self.vehicle)
			self.validate_owned_truck_material_compatibility()
			if not self.driver:
				frappe.throw(_("Driver is required for own fleet Transport Trips."))
			return

		self.validate_hired_execution()
		self.validate_assignment_availability()

	def validate_assignment_availability(self):
		if self.status not in VEHICLE_RESERVED_STATUSES:
			return

		lock_assignment_resources(self)
		if self.driver:
			driver = frappe.db.get_value("Truck Driver", self.driver, ["status"], as_dict=True)
			if not driver:
				frappe.throw(_("Driver must be a valid Truck Driver."))
			if driver.status != "Active":
				frappe.throw(_("Only Active Truck Drivers can be assigned to Transport Trips."))
			existing_trip = get_active_driver_trip(self.driver, exclude_name=self.name)
			if existing_trip:
				frappe.throw(
					_("Driver {0} is already assigned to active Trip {1}.").format(self.driver, existing_trip)
				)

		if self.execution_source == "OWN":
			existing_trip = get_active_vehicle_trip(self.vehicle, exclude_name=self.name)
			if existing_trip:
				frappe.throw(
					_("Vehicle {0} is already assigned to active Trip {1}. Please select another available vehicle.").format(
						self.vehicle, existing_trip
					)
				)
		elif self.hired_vehicle:
			existing_trip = get_active_hired_vehicle_trip(self.hired_vehicle, exclude_name=self.name)
			if existing_trip:
				frappe.throw(
					_("Hired Vehicle {0} is already assigned to active Trip {1}.").format(
						self.hired_vehicle, existing_trip
					)
				)

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
		job_mode = frappe.db.get_value("Transport Job", self.transport_job, "quantity_mode")
		is_open_job = job_mode == OPEN_QUANTITY_MODE
		if not isfinite(planned_quantity) or planned_quantity < 0 or (not is_open_job and planned_quantity <= 0):
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
		if self.is_open_quantity_job():
			if self.get("loading_stops"):
				frappe.throw(_("Open Transport Trips use one selected loading point, not quantity-allocated loading stops."))
		else:
			validate_loading_stop_rows(self.get("loading_stops"), self.planned_quantity, _("Transport Trip"))

	def is_open_quantity_job(self):
		return bool(
			self.transport_job
			and frappe.db.get_value("Transport Job", self.transport_job, "quantity_mode") == OPEN_QUANTITY_MODE
		)

	def validate_planned_loading_point(self):
		self.validate_open_job_route()

	def validate_open_job_route(self):
		if not self.is_open_quantity_job():
			return
		job = frappe.get_doc("Transport Job", self.transport_job)
		# 1. Loading point validation
		permitted_loading_points = {
			row.loading_location for row in job.permitted_loading_points if row.loading_location
		}
		if not permitted_loading_points:
			frappe.throw(_("Open Transport Jobs must have at least one permitted loading point."))
		if self.loading_site not in permitted_loading_points:
			frappe.throw(
				_("Planned Loading Location {0} must be one of the Job's permitted loading points.").format(
					self.loading_site
				)
			)

		# 2. Destination validation
		permitted_destinations = set(job.get_permitted_destinations())
		if self.unloading_site not in permitted_destinations:
			frappe.throw(
				_("Destination {0} is not permitted for Transport Job {1}.").format(
					self.unloading_site, self.transport_job
				)
			)

		# 3. Route combination validation (material, loading_location, unloading_location)
		valid_routes = job.get_permitted_routes()
		is_valid_route = any(
			r["loading_location"] == self.loading_site and r["unloading_location"] == self.unloading_site
			for r in valid_routes
		)
		if not is_valid_route:
			frappe.throw(
				_("Route combination from {0} to {1} for Material {2} is not authorized for Transport Job {3}.").format(
					self.loading_site,
					self.unloading_site,
					self.material,
					self.transport_job,
				)
			)

	def validate_protected_loading_and_rate_fields(self):
		if self.is_new():
			protected = (
				"loading_document",
				"actual_material",
				"actual_loading_location",
				"actual_loading_date",
				"loading_verified_by",
				"loading_verified_at",
				"applied_rate_snapshot",
				"applied_rate_loading_date",
				"applied_rate_per_ton",
				"applied_rate_currency",
				"rate_locked_at",
				"rate_block_reason",
			)
			if any(self.get(fieldname) for fieldname in protected) and not self.flags.get("loading_confirmation"):
				frappe.throw(_("Verified loading facts and commercial rate fields can only be set by the loading operation."))
			if (
				self.commercial_rate_status not in {"NOT_APPLICABLE", "PENDING_CONFIRMATION"}
				and not self.flags.get("loading_confirmation")
			):
				frappe.throw(_("Commercial rate status can only be set by the loading operation."))
			if self.flags.get("dispatch_assignment_workflow") and self.commercial_rate_status not in {
				"NOT_APPLICABLE",
				"PENDING_CONFIRMATION",
			}:
				frappe.throw(_("Dispatch assignment cannot set a commercial rate status."))
			return

		previous = frappe.db.get_value(
			self.doctype,
			self.name,
			[
				"loading_document",
				"actual_material",
				"actual_loading_location",
				"actual_loading_date",
				"loading_verified_by",
				"loading_verified_at",
				"commercial_rate_status",
				"applied_rate_snapshot",
				"applied_rate_loading_date",
				"applied_rate_per_ton",
				"applied_rate_currency",
				"rate_locked_at",
				"rate_block_reason",
			],
			as_dict=True,
		)
		changed = [
			fieldname
			for fieldname in previous
			if self.get(fieldname) != previous.get(fieldname)
		]
		if changed and not self.flags.get("loading_confirmation"):
			frappe.throw(_("Verified loading facts and commercial rate fields can only be changed by the loading operation."))
		if previous.rate_locked_at and changed:
			frappe.throw(_("The applied quotation rate is locked and cannot be changed."))
		if previous.actual_loading_date and any(
			self.get(fieldname) != frappe.db.get_value(self.doctype, self.name, fieldname)
			for fieldname in ("loaded_quantity", "loading_datetime")
		):
			frappe.throw(_("Verified loading quantity and date are immutable after loading confirmation."))
		if previous.actual_loading_date and frappe.db.get_value(
			"Transport Job", self.transport_job, "quantity_mode"
		) == OPEN_QUANTITY_MODE:
			previous_plan = frappe.db.get_value(
				self.doctype,
				self.name,
				["material", "loading_site", "unloading_site", "trip_date"],
				as_dict=True,
			)
			if any(
				self.get(fieldname) != previous_plan.get(fieldname)
				for fieldname in ("material", "loading_site", "unloading_site", "trip_date")
			):
				frappe.throw(_("Planned Trip details cannot be changed after actual loading is confirmed."))

	def validate_verified_delivery(self):
		protected = (
			"verified_delivery_document",
			"verified_delivered_quantity",
			"delivery_verified_by",
			"delivery_verified_at",
		)
		if self.is_new():
			if any(self.get(fieldname) for fieldname in protected) and not self.flags.get("delivery_confirmation"):
				frappe.throw(_("Verified delivery facts can only be set by the delivery verification operation."))
			return

		previous = frappe.db.get_value(self.doctype, self.name, (*protected, "delivered_quantity"), as_dict=True)
		changed = [fieldname for fieldname in protected if self.get(fieldname) != previous.get(fieldname)]
		job_mode = frappe.db.get_value("Transport Job", self.transport_job, "quantity_mode")
		if changed and not self.flags.get("delivery_confirmation"):
			frappe.throw(_("Verified delivery facts can only be changed by the delivery verification operation."))
		if previous.delivery_verified_at and changed:
			frappe.throw(_("Verified delivery facts are immutable; create a controlled correction record."))
		if (
			job_mode == OPEN_QUANTITY_MODE
			and previous.delivery_verified_at
			and self.delivered_quantity != previous.delivered_quantity
		):
			frappe.throw(_("Delivered Quantity is immutable after Operations verification."))
		if self.delivery_verified_at and (
			not self.verified_delivery_document
			or flt(self.verified_delivered_quantity, 6) <= 0
			or flt(self.delivered_quantity, 6) != flt(self.verified_delivered_quantity, 6)
			or not self.delivery_verified_by
		):
			frappe.throw(_("Verified delivery requires its approved document, quantity, and reviewer audit details."))

	def validate_open_loading_confirmation(self):
		job_mode = frappe.db.get_value("Transport Job", self.transport_job, "quantity_mode")
		if job_mode != OPEN_QUANTITY_MODE:
			return
		previous_status = None if self.is_new() else frappe.db.get_value(self.doctype, self.name, "status")
		if self.is_new() and not self.flags.get("dispatch_assignment_workflow"):
			frappe.throw(_("Open Transport Trips must be created through the Dispatch assignment operation."))
		if self.status == "LOADED" and previous_status != "LOADED":
			if not self.flags.get("loading_confirmation"):
				frappe.throw(_("Open Transport Trips must be loaded through the verified loading confirmation operation."))
			if not all((
				self.loading_document,
				self.actual_material,
				self.actual_loading_location,
				self.actual_loading_date,
				self.loaded_quantity,
				self.loading_verified_by,
				self.loading_verified_at,
			)):
				frappe.throw(_("Open Transport Trips require verified loading document facts before loading confirmation."))
		if self.status in {"IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"} and not self.actual_loading_date:
			frappe.throw(_("Open Transport Trips require verified actual loading facts before leaving ASSIGNED status."))

	def set_loading_stops_from_job_if_missing(self):
		if not self.transport_job or self.get("loading_stops"):
			return
		job = frappe.get_doc("Transport Job", self.transport_job)
		if job.get("loading_stops"):
			copy_loading_stops(
				job,
				self,
				target_quantity=self.planned_quantity,
				source_quantity=job.requested_quantity,
			)

	def scale_job_loading_stops_to_trip_quantity(self):
		if not self.transport_job or not self.get("loading_stops") or not self.planned_quantity:
			return

		job_requested_quantity = flt(
			frappe.db.get_value("Transport Job", self.transport_job, "requested_quantity"),
			6,
		)
		stop_total = flt(sum(flt(stop.planned_quantity, 6) for stop in self.loading_stops), 6)
		if stop_total == flt(self.planned_quantity, 6) or stop_total != job_requested_quantity:
			return

		scaled_quantities = get_scaled_stop_quantities(
			self.loading_stops,
			target_quantity=self.planned_quantity,
			source_quantity=job_requested_quantity,
		)
		for index, stop in enumerate(self.loading_stops):
			stop.planned_quantity = scaled_quantities[index]

	def validate_status_transition(self):
		if self.status not in ALLOWED_STATUSES:
			frappe.throw(_("Invalid Transport Trip status {0}.").format(self.status))

		if self.is_new():
			if self.status == "ASSIGNED" and self.flags.get("dispatch_assignment_workflow"):
				return
			if self.status != "PLANNED":
				frappe.throw(_("New Transport Trips must start as PLANNED or use the Dispatch assignment operation."))
			return

		previous_status = frappe.db.get_value(self.doctype, self.name, "status")
		if previous_status == self.status:
			return

		if previous_status == "CLOSED":
			frappe.throw(_("Closed Transport Trips cannot be reopened or changed."))

		if self.flags.get("driver_portal_start_trip") and previous_status == "ASSIGNED" and self.status == "IN_TRANSIT":
			if frappe.db.get_value("Transport Job", self.transport_job, "quantity_mode") == OPEN_QUANTITY_MODE:
				self.require_verified_open_loading_facts()
			return

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
		if self.status == "IN_TRANSIT" and frappe.db.get_value(
			"Transport Job", self.transport_job, "quantity_mode"
		) == OPEN_QUANTITY_MODE:
			self.require_verified_open_loading_facts()

	def require_verified_open_loading_facts(self):
		if not all((
			self.loading_document,
			self.actual_material,
			self.actual_loading_location,
			self.actual_loading_date,
			self.loading_verified_by,
			self.loading_verified_at,
		)):
			frappe.throw(_("Open Transport Trips require verified actual loading facts before starting transit."))

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
		if job.quantity_mode == OPEN_QUANTITY_MODE:
			return
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
	if job.quantity_mode != OPEN_QUANTITY_MODE and flt(job.remaining_quantity, 6) <= 0:
		frappe.throw(_("This Transport Job is fully delivered. No remaining quantity is available for a new Trip."))
	res = {
		"transport_job": job.name,
		"trip_date": job.requested_date,
		"loading_site": job.loading_site,
		"unloading_site": job.unloading_site,
		"material": job.material,
		"uom": TON_UOM,
		"quantity_mode": job.quantity_mode,
		"loading_stops": [
			{
				"loading_location": stop.loading_location,
				"planned_quantity": stop.planned_quantity,
				"notes": stop.get("notes"),
			}
			for stop in job.get("loading_stops") or []
		],
	}
	if job.quantity_mode == OPEN_QUANTITY_MODE:
		res["permitted_loading_points"] = [
			row.loading_location for row in (job.permitted_loading_points or []) if row.loading_location
		]
		res["permitted_destinations"] = job.get_permitted_destinations()
		res["permitted_routes"] = job.get_permitted_routes()
	return res


@frappe.whitelist()
def get_trip_route_options(transport_job, loading_site=None):
	if not transport_job:
		frappe.throw(_("Transport Job is required."))
	job = frappe.get_doc("Transport Job", transport_job)
	job.check_permission("read")

	if job.quantity_mode != OPEN_QUANTITY_MODE:
		return {
			"quantity_mode": job.quantity_mode,
			"material": job.material,
			"loading_points": [job.loading_site] if job.loading_site else [],
			"destinations": [job.unloading_site] if job.unloading_site else [],
			"routes": [
				{"loading_location": job.loading_site, "unloading_location": job.unloading_site}
			] if job.loading_site and job.unloading_site else [],
		}

	loading_points = [
		row.loading_location for row in (job.permitted_loading_points or []) if row.loading_location
	]
	destinations = job.get_permitted_destinations()
	routes = job.get_permitted_routes()

	if loading_site:
		routes = [r for r in routes if r["loading_location"] == loading_site]
		destinations = sorted(list({r["unloading_location"] for r in routes}))

	return {
		"quantity_mode": job.quantity_mode,
		"material": job.material,
		"loading_points": loading_points,
		"destinations": destinations,
		"routes": routes,
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
def create_assigned_transport_trip(
	transport_job,
	vehicle=None,
	driver=None,
	material=None,
	loading_site=None,
	unloading_site=None,
	trip_date=None,
	planned_quantity=None,
	execution_source="OWN",
	transporter=None,
	hired_vehicle=None,
	hired_driver=None,
):
	require_trip_dispatch_permission("create")
	if not frappe.db.exists("Transport Job", transport_job):
		frappe.throw(_("Transport Job must exist."))
	job = frappe.get_doc("Transport Job", transport_job)
	job.check_permission("read")
	if job.docstatus == 2 or job.status == "Cancelled":
		frappe.throw(_("Cancelled Transport Jobs cannot receive new Trips."))
	if not driver and execution_source == "OWN":
		frappe.throw(_("A Truck Driver must be selected when assigning a Transport Trip."))
	if not material:
		material = job.material
	if not trip_date:
		trip_date = job.requested_date or frappe.utils.today()
	if not all((material, loading_site, unloading_site, trip_date)):
		frappe.throw(_("Planned material, loading point, destination, and Trip date are required."))
	if job.quantity_mode != OPEN_QUANTITY_MODE and planned_quantity in (None, ""):
		frappe.throw(_("Planned Quantity is required for Fixed Quantity Jobs."))

	trip = frappe.new_doc("Transport Trip")
	trip.update({
		"transport_job": job.name,
		"trip_date": trip_date,
		"status": "ASSIGNED",
		"execution_source": execution_source,
		"vehicle": vehicle,
		"driver": driver,
		"material": material,
		"loading_site": loading_site,
		"unloading_site": unloading_site,
		"planned_quantity": planned_quantity or 0,
		"uom": TON_UOM,
		"transporter": transporter,
		"hired_vehicle": hired_vehicle,
		"hired_driver": hired_driver,
	})
	trip.flags.dispatch_assignment_workflow = True
	trip.insert()
	return {
		"name": trip.name,
		"status": trip.status,
		"transport_job": trip.transport_job,
		"driver": trip.driver,
		"vehicle": trip.vehicle,
		"hired_vehicle": trip.hired_vehicle,
	}


@frappe.whitelist()
def verify_trip_loading_document(
	document_name,
	verified_material,
	verified_loading_location,
	verified_loading_date,
	verified_loaded_quantity,
	correction_reason=None,
):
	require_trip_dispatch_permission("verify loading")
	if not frappe.db.exists("Transport Trip Document", document_name):
		frappe.throw(_("Transport Trip Document must exist."))
	document = frappe.get_doc("Transport Trip Document", document_name)
	trip = frappe.get_doc("Transport Trip", document.transport_trip, for_update=True)
	document = frappe.get_doc("Transport Trip Document", document_name, for_update=True)
	document.check_permission("read")
	if document.document_type != "LOADING_PAPER":
		frappe.throw(_("Only a LOADING_PAPER document can verify loading facts."))
	trip.check_permission("read")
	if document.transport_trip != trip.name:
		frappe.throw(_("The Loading Paper Transport Trip changed while it was being reviewed; reload and retry."))
	if trip.status != "ASSIGNED":
		frappe.throw(_("Loading Papers can only be verified while the Transport Trip is ASSIGNED."))
	if document.verification_status == "APPROVED":
		if (
			document.verified_material == verified_material
			and document.verified_loading_location == verified_loading_location
			and getdate(document.verified_loading_date) == getdate(verified_loading_date)
			and flt(document.verified_loaded_quantity, 6) == flt(verified_loaded_quantity, 6)
		):
			return {"name": document.name, "verification_status": "APPROVED", "already_verified": True}
		frappe.throw(_("This Loading Paper is already verified; corrections require a new controlled document."))
	if document.verification_status != "PENDING_REVIEW":
		frappe.throw(_("Only a pending Loading Paper can be verified."))
	if not all((verified_material, verified_loading_location, verified_loading_date)):
		frappe.throw(_("Verified material, loading location, and loading date are required."))
	if not frappe.db.exists("Cargo Types", verified_material):
		frappe.throw(_("Verified actual Material must exist."))
	if not frappe.db.get_value("Cargo Types", verified_material, "active"):
		frappe.throw(_("Verified actual Material must be active."))
	validate_transport_location_usage(
		verified_loading_location,
		{"Loading", "Both"},
		_("Verified Actual Loading Location"),
	)
	loading_date = getdate(verified_loading_date)
	if loading_date > getdate():
		frappe.throw(_("Verified Loading Date cannot be in the future."))
	quantity = flt(verified_loaded_quantity, 6)
	if not isfinite(quantity) or quantity <= 0:
		frappe.throw(_("Verified Loaded Quantity must be greater than zero."))
	if loading_facts_were_corrected(document, verified_material, verified_loading_location, loading_date, quantity):
		if not correction_reason or not correction_reason.strip():
			frappe.throw(_("A correction reason is required when verified values differ from extracted values."))

	document.verified_material = verified_material
	document.verified_loading_location = verified_loading_location
	document.verified_loading_date = loading_date
	document.verified_loaded_quantity = quantity
	document.verification_status = "APPROVED"
	document.verified_by = frappe.session.user
	document.verified_at = now_datetime()
	if correction_reason:
		document.review_notes = correction_reason.strip()
	document.flags.loading_document_review = True
	document.save(ignore_permissions=True)
	return {"name": document.name, "verification_status": document.verification_status, "already_verified": False}


@frappe.whitelist()
def reject_trip_loading_document(document_name, reason):
	require_trip_dispatch_permission("verify loading")
	if not reason or not reason.strip():
		frappe.throw(_("A review reason is required when rejecting a Loading Paper."))
	document = frappe.get_doc("Transport Trip Document", document_name)
	trip = frappe.get_doc("Transport Trip", document.transport_trip, for_update=True)
	document = frappe.get_doc("Transport Trip Document", document_name, for_update=True)
	document.check_permission("read")
	trip.check_permission("read")
	if document.transport_trip != trip.name:
		frappe.throw(_("The Loading Paper Transport Trip changed while it was being reviewed; reload and retry."))
	if trip.status != "ASSIGNED":
		frappe.throw(_("Loading Papers can only be reviewed while the Transport Trip is ASSIGNED."))
	if document.document_type != "LOADING_PAPER" or document.verification_status != "PENDING_REVIEW":
		frappe.throw(_("Only a pending LOADING_PAPER document can be rejected."))
	document.verification_status = "REJECTED"
	document.review_notes = reason.strip()
	document.verified_by = frappe.session.user
	document.verified_at = now_datetime()
	document.flags.loading_document_review = True
	document.save(ignore_permissions=True)
	return {"name": document.name, "verification_status": document.verification_status}


@frappe.whitelist()
def verify_trip_delivery_document(document_name, verified_delivery_date, verified_delivered_quantity):
	require_trip_dispatch_permission("verify delivery")
	if not frappe.db.exists("Transport Trip Document", document_name):
		frappe.throw(_("Transport Trip Document must exist."))
	document = frappe.get_doc("Transport Trip Document", document_name)
	trip = frappe.get_doc("Transport Trip", document.transport_trip, for_update=True)
	document = frappe.get_doc("Transport Trip Document", document_name, for_update=True)
	document.check_permission("read")
	trip.check_permission("read")
	if document.document_type != "OFFLOADING_PAPER":
		frappe.throw(_("Only an OFFLOADING_PAPER document can verify delivery facts."))
	if document.transport_trip != trip.name:
		frappe.throw(_("The Offloading Paper Transport Trip changed while it was being reviewed; reload and retry."))
	if trip.status not in {"DELIVERED", "POD_RECEIVED", "CLOSED"}:
		frappe.throw(_("Offloading Papers can only be verified after the Transport Trip is delivered."))
	if document.verification_status == "APPROVED":
		if (
			getdate(document.verified_delivery_date) == getdate(verified_delivery_date)
			and flt(document.verified_delivered_quantity, 6) == flt(verified_delivered_quantity, 6)
		):
			return {"name": document.name, "verification_status": "APPROVED", "already_verified": True}
		frappe.throw(_("This Offloading Paper is already verified; corrections require a new controlled document."))
	if document.verification_status != "PENDING_REVIEW":
		frappe.throw(_("Only a pending Offloading Paper can be verified."))
	if not verified_delivery_date:
		frappe.throw(_("Verified Delivery Date is required."))
	delivery_date = getdate(verified_delivery_date)
	if delivery_date > getdate():
		frappe.throw(_("Verified Delivery Date cannot be in the future."))
	quantity = flt(verified_delivered_quantity, 6)
	if not isfinite(quantity) or quantity <= 0:
		frappe.throw(_("Verified Delivered Quantity must be greater than zero."))
	if quantity > flt(trip.loaded_quantity, 6):
		frappe.throw(_("Verified Delivered Quantity cannot exceed Loaded Quantity."))

	document.verified_delivery_date = delivery_date
	document.verified_delivered_quantity = quantity
	document.verification_status = "APPROVED"
	document.verified_by = frappe.session.user
	document.verified_at = now_datetime()
	document.flags.delivery_document_review = True
	document.save(ignore_permissions=True)

	trip.verified_delivery_document = document.name
	trip.verified_delivered_quantity = quantity
	trip.delivery_verified_by = document.verified_by
	trip.delivery_verified_at = document.verified_at
	trip.delivered_quantity = quantity
	trip.flags.delivery_confirmation = True
	trip.save()
	trip.add_comment(
		"Comment",
		_("Delivery verified from Offloading Paper {0}; verified quantity: {1} TON.").format(document.name, quantity),
	)
	return {
		"name": document.name,
		"verification_status": document.verification_status,
		"verified_delivered_quantity": quantity,
		"already_verified": False,
	}


@frappe.whitelist()
def reject_trip_delivery_document(document_name, reason):
	require_trip_dispatch_permission("verify delivery")
	if not reason or not reason.strip():
		frappe.throw(_("A review reason is required when rejecting an Offloading Paper."))
	document = frappe.get_doc("Transport Trip Document", document_name)
	trip = frappe.get_doc("Transport Trip", document.transport_trip, for_update=True)
	document = frappe.get_doc("Transport Trip Document", document_name, for_update=True)
	document.check_permission("read")
	trip.check_permission("read")
	if document.transport_trip != trip.name:
		frappe.throw(_("The Offloading Paper Transport Trip changed while it was being reviewed; reload and retry."))
	if trip.status not in {"DELIVERED", "POD_RECEIVED", "CLOSED"}:
		frappe.throw(_("Offloading Papers can only be reviewed after the Transport Trip is delivered."))
	if document.document_type != "OFFLOADING_PAPER" or document.verification_status != "PENDING_REVIEW":
		frappe.throw(_("Only a pending OFFLOADING_PAPER document can be rejected."))
	document.verification_status = "REJECTED"
	document.review_notes = reason.strip()
	document.verified_by = frappe.session.user
	document.verified_at = now_datetime()
	document.flags.delivery_document_review = True
	document.save(ignore_permissions=True)
	return {"name": document.name, "verification_status": document.verification_status}


@frappe.whitelist()
def confirm_trip_loading(transport_trip, loading_document=None):
	require_trip_dispatch_permission("confirm loading")
	trip = frappe.get_doc("Transport Trip", transport_trip, for_update=True)
	trip.check_permission("write")
	if trip.status == "LOADED" and trip.loading_document and trip.loading_verified_at:
		return build_trip_commercial_state(trip, already_confirmed=True)
	if trip.status != "ASSIGNED":
		frappe.throw(_("Loading can only be confirmed for an ASSIGNED Transport Trip."))
	document_name = loading_document or trip.loading_document
	if not document_name or not frappe.db.exists("Transport Trip Document", document_name):
		frappe.throw(_("A verified Loading Paper must be linked to the Transport Trip."))

	document = frappe.get_doc("Transport Trip Document", document_name, for_update=True)
	if (
		document.transport_trip != trip.name
		or document.document_type != "LOADING_PAPER"
		or document.verification_status != "APPROVED"
	):
		frappe.throw(_("The linked Loading Paper must be approved and belong to this Transport Trip."))

	trip.actual_material = document.verified_material
	trip.actual_loading_location = document.verified_loading_location
	trip.actual_loading_date = document.verified_loading_date
	trip.loading_document = document.name
	trip.loading_verified_by = document.verified_by
	trip.loading_verified_at = document.verified_at
	trip.loaded_quantity = document.verified_loaded_quantity
	trip.loading_datetime = f"{getdate(document.verified_loading_date)} 00:00:00"
	trip.commercial_rate_status = "NOT_APPLICABLE"
	trip.rate_block_reason = None

	job = frappe.get_doc("Transport Job", trip.transport_job)
	if job.quantity_mode == OPEN_QUANTITY_MODE:
		from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
			resolve_quotation_sales_order_rate,
		)

		rate = resolve_quotation_sales_order_rate(
			job.sales_order,
			document.verified_material,
			document.verified_loading_location,
			trip.unloading_site,
			document.verified_loading_date,
			allow_unresolved=True,
		)
		trip.applied_rate_loading_date = document.verified_loading_date
		if rate.get("blocked_reason"):
			trip.commercial_rate_status = "RATE_BLOCKED"
			trip.rate_block_reason = rate["blocked_reason"]
		else:
			trip.applied_rate_snapshot = rate["rate_snapshot"]
			trip.applied_rate_per_ton = rate["rate"]
			trip.applied_rate_currency = rate["currency"]
			trip.commercial_rate_status = "CONFIRMED"
			trip.rate_locked_at = now_datetime()

	trip.status = "LOADED"
	trip.flags.loading_confirmation = True
	trip.save()
	trip.add_comment(
		"Comment",
		_("Loading confirmed from verified document {0}; commercial rate state: {1}.").format(
			document.name, trip.commercial_rate_status
		),
	)
	return build_trip_commercial_state(trip, already_confirmed=False)


@frappe.whitelist()
def get_trip_execution_state(transport_trip):
	trip = frappe.get_doc("Transport Trip", transport_trip)
	trip.check_permission("read")
	return build_trip_commercial_state(trip)


def build_trip_commercial_state(trip, already_confirmed=False):
	return {
		"name": trip.name,
		"status": trip.status,
		"planned": {
			"material": trip.material,
			"loading_location": trip.loading_site,
			"destination": trip.unloading_site,
			"trip_date": trip.trip_date,
			"quantity": flt(trip.planned_quantity, 6),
		},
		"actual": {
			"document": trip.loading_document,
			"material": trip.actual_material,
			"loading_location": trip.actual_loading_location,
			"loading_date": trip.actual_loading_date,
			"loaded_quantity": flt(trip.loaded_quantity, 6),
			"verified_by": trip.loading_verified_by,
			"verified_at": trip.loading_verified_at,
		},
		"commercial_rate": {
			"status": trip.commercial_rate_status,
			"snapshot": trip.applied_rate_snapshot,
			"loading_date": trip.applied_rate_loading_date,
			"rate_per_ton": trip.applied_rate_per_ton,
			"currency": trip.applied_rate_currency,
			"locked_at": trip.rate_locked_at,
			"blocked_reason": trip.rate_block_reason,
		},
		"already_confirmed": already_confirmed,
	}


def loading_facts_were_corrected(document, material, loading_location, loading_date, quantity):
	if document.extracted_material:
		material_name = frappe.db.get_value("Cargo Types", material, "cargo_name")
		if document.extracted_material not in {material, material_name}:
			return True
	if document.extracted_station_or_gate:
		location_name = frappe.db.get_value("Transport Location", loading_location, "location")
		if document.extracted_station_or_gate not in {loading_location, location_name}:
			return True
	if document.extracted_document_datetime and getdate(document.extracted_document_datetime) != loading_date:
		return True
	if document.extracted_net_weight and flt(document.extracted_net_weight, 6) != quantity:
		return True
	return False


def require_trip_dispatch_permission(action):
	if not TRIP_DISPATCH_ROLES.intersection(frappe.get_roles()):
		frappe.throw(_("You are not permitted to {0} for Transport Trips.").format(action), frappe.PermissionError)
	if action == "create" and not frappe.has_permission("Transport Trip", ptype="create"):
		frappe.throw(_("You do not have permission to create Transport Trips."), frappe.PermissionError)
	if not frappe.has_permission("Transport Trip", ptype="write"):
		frappe.throw(_("You do not have permission to update Transport Trips."), frappe.PermissionError)


@frappe.whitelist()
def calculate_charges(transport_trip):
	if not transport_trip:
		frappe.throw(_("Transport Trip is required."))
	return apply_transport_trip_charges(transport_trip)


def lock_transport_job(transport_job):
	rows = frappe.db.sql(
		"""
		select name, requested_quantity, quantity_mode
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
	sql_values.append(TRIP_RESOURCE_ACTIVE_STATUSES)
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


def get_active_driver_trip(driver, exclude_name=None):
	return get_active_resource_trip("driver", driver, exclude_name)


def get_active_hired_vehicle_trip(hired_vehicle, exclude_name=None):
	return get_active_resource_trip("hired_vehicle", hired_vehicle, exclude_name)


def get_active_resource_trip(fieldname, value, exclude_name=None):
	if fieldname not in {"driver", "hired_vehicle"}:
		frappe.throw(_("Unsupported Transport Trip resource field."))
	filters = [f"`{fieldname}` = %s", "status in %s"]
	values = [value, TRIP_RESOURCE_ACTIVE_STATUSES]
	if exclude_name:
		filters.append("name != %s")
		values.append(exclude_name)
	rows = frappe.db.sql(
		f"""
		select name
		from `tabTransport Trip`
		where {' and '.join(filters)}
		order by creation asc
		limit 1
		for update
		""",
		tuple(values),
		as_dict=True,
	)
	return rows[0].name if rows else None


def lock_assignment_resources(trip):
	resources = set()
	current = {
		"execution_source": trip.execution_source,
		"vehicle": trip.vehicle,
		"hired_vehicle": trip.hired_vehicle,
		"driver": trip.driver,
	}
	for fieldname, doctype in (
		("vehicle", "Truck"),
		("hired_vehicle", "Hired Vehicle"),
		("driver", "Truck Driver"),
	):
		if current.get(fieldname):
			resources.add((doctype, current[fieldname]))
	if not trip.is_new():
		previous = frappe.db.get_value(
			trip.doctype,
			trip.name,
			["execution_source", "vehicle", "hired_vehicle", "driver"],
			as_dict=True,
		)
		for fieldname, doctype in (
			("vehicle", "Truck"),
			("hired_vehicle", "Hired Vehicle"),
			("driver", "Truck Driver"),
		):
			if previous.get(fieldname):
				resources.add((doctype, previous[fieldname]))

	for doctype, name in sorted(resources):
		frappe.db.sql(f"select name from `tab{doctype}` where name = %s for update", name)
