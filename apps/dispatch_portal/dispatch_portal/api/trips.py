"""Dispatcher trips API - listing, detail and status orchestration.

Status transitions, charge recalculation and every business rule stay in
``transport_management``; this module only orchestrates dispatcher intent and
enforces dispatcher-specific authorisation.
"""

from __future__ import annotations

import frappe

from dispatch_portal.services.dispatch_access import require_console_access
from dispatch_portal.services.trip_console import (
	get_trip_doc,
	list_trips,
	normalize_limit,
	normalize_offset,
	serialize_trip_detail,
	serialize_trip_summary,
	to_int,
)

ALLOWED_TRANSITIONS = (
	"PLANNED",
	"ASSIGNED",
	"LOADED",
	"IN_TRANSIT",
	"DELIVERED",
	"POD_RECEIVED",
	"CLOSED",
	"EXCEPTION",
	"CANCELLED",
)


@frappe.whitelist()
def get_trips(filters=None, start=0, page_length=25, order_by=None):
	"""Paginated Transport Trip rows for the dispatcher trips grid."""
	require_console_access()
	trips = list_trips(
		filters=filters,
		start=normalize_offset(start),
		page_length=normalize_limit(page_length, default=25, maximum=200),
		order_by=order_by or "modified desc",
	)
	return {
		"start": normalize_offset(start),
		"page_length": normalize_limit(page_length, default=25, maximum=200),
		"trips": [serialize_trip_summary(trip) for trip in trips],
	}


@frappe.whitelist()
def get_trip_count(filters=None):
	require_console_access()
	from dispatch_portal.services.trip_console import get_trip_count as _count

	return {"count": _count(filters)}


@frappe.whitelist()
def get_trip(trip_id):
	"""Full dispatcher view of one Transport Trip."""
	require_console_access()
	trip = get_trip_doc(trip_id)
	return serialize_trip_detail(trip)


@frappe.whitelist(methods=["POST"])
def transition_trip(trip_id, status):
	"""Move a trip through the TMS status workflow via its own whitelisted API."""
	require_console_access()
	status = (status or "").strip().upper()
	if status not in ALLOWED_TRANSITIONS:
		frappe.throw("Invalid Transport Trip status {0}.".format(status))

	from transport_management.transport_management.doctype.transport_trip.transport_trip import (
		transition_trip_status,
	)

	result = transition_trip_status(transport_trip=trip_id, status=status)
	return {"ok": True, "trip": result["name"], "status": result["status"]}


@frappe.whitelist(methods=["POST"])
def assign_trip(trip_id, vehicle=None, driver=None):
	"""Assign a vehicle and driver to a trip; TMS validation still decides."""
	require_console_access()
	if not vehicle and not driver:
		frappe.throw("Provide a vehicle or a driver to assign.")

	trip = get_trip_doc(trip_id)
	if trip.status in ("CLOSED", "CANCELLED"):
		frappe.throw("Transport Trip {0} is {1} and cannot be assigned.".format(trip.name, trip.status))

	if vehicle:
		if not frappe.has_permission("Truck", ptype="read"):
			frappe.throw("You do not have permission to read Truck.")
		if not frappe.db.exists("Truck", vehicle):
			frappe.throw("Truck {0} does not exist.".format(vehicle))
		trip.execution_source = "OWN"
		trip.vehicle = vehicle

	if driver:
		if not frappe.has_permission("Truck Driver", ptype="read"):
			frappe.throw("You do not have permission to read Truck Driver.")
		if not frappe.db.exists("Truck Driver", driver):
			frappe.throw("Truck Driver {0} does not exist.".format(driver))
		trip.driver = driver

	if trip.status == "PLANNED" and trip.vehicle and trip.driver:
		trip.status = "ASSIGNED"

	trip.save()
	return {"ok": True, "trip": serialize_trip_summary(trip)}


@frappe.whitelist()
def get_assignment_options(trip_id=None):
	"""Available trucks/drivers for the assignment dialog, from TMS masters."""
	require_console_access()

	reserved_vehicles = frappe.get_all(
		"Transport Trip",
		filters={
			"execution_source": "OWN",
			"status": ["in", ["PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT"]],
		},
		pluck="vehicle",
		limit_page_length=0,
	)

	trucks = frappe.get_all(
		"Truck",
		filters={"disabled": 0, "status": "Idle"},
		fields=["name", "truck_number", "vehicle_type", "capacity", "capacity_uom", "status"],
		order_by="truck_number asc",
		limit_page_length=200,
	)
	if trip_id:
		current = frappe.db.get_value("Transport Trip", trip_id, "vehicle")
		if current:
			trucks.extend(
				frappe.get_all(
					"Truck",
					filters={"name": current},
					fields=[
						"name",
						"truck_number",
						"vehicle_type",
						"capacity",
						"capacity_uom",
						"status",
					],
					limit_page_length=1,
				)
			)

	seen = set()
	available = []
	for truck in trucks:
		if truck.name in seen:
			continue
		seen.add(truck.name)
		row = dict(truck)
		row["reserved"] = truck.name in set(reserved_vehicles)
		available.append(row)

	drivers = frappe.get_all(
		"Truck Driver",
		filters={"status": "Active"},
		fields=["name", "full_name", "cell_number", "in_trip", "status"],
		order_by="full_name asc",
		limit_page_length=200,
	)

	return {
		"trucks": sorted(available, key=lambda row: (row["reserved"], row["name"] or "")),
		"drivers": [dict(driver) for driver in drivers],
	}


@frappe.whitelist()
def get_status_flow():
	"""Status metadata used to render the trip status controls."""
	require_console_access()
	return {
		"statuses": [
			{"value": "PLANNED", "label": "Planned", "indicator": "gray"},
			{"value": "ASSIGNED", "label": "Assigned", "indicator": "blue"},
			{"value": "LOADED", "label": "Loaded", "indicator": "purple"},
			{"value": "IN_TRANSIT", "label": "In Transit", "indicator": "orange"},
			{"value": "DELIVERED", "label": "Delivered", "indicator": "green"},
			{"value": "POD_RECEIVED", "label": "POD Received", "indicator": "green"},
			{"value": "EXCEPTION", "label": "Exception", "indicator": "red"},
			{"value": "CLOSED", "label": "Closed", "indicator": "darkgrey"},
			{"value": "CANCELLED", "label": "Cancelled", "indicator": "red"},
		]
	}
