"""Read-only Driver Portal trip listing."""

from __future__ import annotations

from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, now_datetime

from transport_management.loading_stops import serialize_loading_stops
from transport_management.services.driver_portal_auth import require_current_driver_identity
from transport_management.services.driver_portal_documents import get_trip_document_summary
from transport_management.transport_management.doctype.transport_charge_rule.transport_charge_rule import (
	calculate_transport_trip_charges,
)

UPCOMING_STATUSES = {"PLANNED"}
ACTIVE_STATUSES = {"ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED"}
COMPLETED_STATUSES = {"CLOSED"}
CANCELLED_STATUSES = {"CANCELLED"}
EXCEPTION_STATUSES = {"EXCEPTION"}
DEFAULT_STATUSES = UPCOMING_STATUSES | ACTIVE_STATUSES
ALL_STATUSES = DEFAULT_STATUSES | COMPLETED_STATUSES | CANCELLED_STATUSES | EXCEPTION_STATUSES
MAX_LIMIT = 100
DEFAULT_LIMIT = 20

PORTAL_OPTIONAL_FIELDS = (
	"driver_portal_status",
	"document_status",
	"loading_paper_status",
	"offloading_paper_status",
	"documents_pending_review",
	"ai_review_status",
)
DOCUMENT_DEFAULTS = {
	"document_status": "MISSING",
	"loading_paper_status": "MISSING",
	"offloading_paper_status": "MISSING",
	"documents_pending_review": 0,
	"ai_review_status": "NOT_PROCESSED",
}
CHARGE_DOCUMENT_TYPES = {
	"RAK Toll": "ABER_TOLL",
	"Sharjah Toll": "SHARJAH_TOLL",
	"FNRC / Extra Charge": "FNRC_RECEIPT",
}


def get_my_trips(view=None, limit=DEFAULT_LIMIT, offset=0, **kwargs) -> dict:
	identity = require_current_driver_identity()
	limit = normalize_limit(limit)
	offset = normalize_offset(offset)
	view = normalize_view(view)
	statuses = get_statuses_for_view(view)

	trips = fetch_driver_trips(identity.truck_driver, statuses)
	total = len(trips)
	sorted_trips = sorted(trips, key=trip_sort_key)
	page = sorted_trips[offset : offset + limit]

	return {
		"ok": True,
		"driver": {
			"truck_driver": identity.truck_driver,
			"driver_name": identity.driver_name,
		},
		"summary": get_driver_trip_summary(identity.truck_driver),
		"limit": limit,
		"offset": offset,
		"total": total,
		"view": view,
		"trips": [serialize_trip(trip) for trip in page],
	}


def get_trip_detail(trip_id: str | None) -> dict:
	identity = require_current_driver_identity()
	trip_id = (str(trip_id or "").strip())
	if not trip_id:
		raise_trip_not_found()

	trip = fetch_trip_detail(trip_id)
	if not trip or trip.driver != identity.truck_driver:
		raise_trip_not_found()

	return {
		"ok": True,
		"trip": serialize_trip_detail(trip),
		"documents": get_document_summary(trip),
		"required_documents": get_required_driver_documents(trip),
		"delivery_requirements": get_driver_delivery_requirements(trip),
		"allowed_actions": get_allowed_driver_actions(trip.status),
	}


def start_driver_trip(trip_id: str | None) -> dict:
	identity = require_current_driver_identity()
	trip_id = (str(trip_id or "").strip())
	if not trip_id:
		raise_trip_not_found()

	lock_trip_for_update(trip_id)
	trip = frappe.get_doc("Transport Trip", trip_id)
	if trip.driver != identity.truck_driver:
		raise_trip_not_found()

	if trip.status == "IN_TRANSIT" and trip.get("driver_started_at"):
		return build_start_trip_response(trip, already_started=True)

	if trip.status != "ASSIGNED":
		raise_invalid_start_state(trip.status)

	started_at = now_datetime()
	trip.flags.driver_portal_start_trip = True
	trip.status = "IN_TRANSIT"
	trip.driver_started_at = started_at
	if not flt(trip.loaded_quantity):
		trip.loaded_quantity = trip.planned_quantity
	if not trip.loading_datetime:
		trip.loading_datetime = started_at
	trip.save(ignore_permissions=True)
	add_driver_trip_started_audit(trip.name, identity, "ASSIGNED", "IN_TRANSIT", started_at)
	return build_start_trip_response(trip)


def mark_driver_trip_delivered(trip_id: str | None) -> dict:
	identity = require_current_driver_identity()
	trip_id = (str(trip_id or "").strip())
	if not trip_id:
		raise_trip_not_found()

	lock_trip_for_update(trip_id)
	trip = frappe.get_doc("Transport Trip", trip_id)
	if trip.driver != identity.truck_driver:
		raise_trip_not_found()

	if trip.status == "DELIVERED" and trip.get("driver_delivered_at"):
		return build_mark_delivered_response(trip, already_delivered=True)

	if trip.status != "IN_TRANSIT":
		raise_invalid_delivery_state(trip.status)

	offloading_document = get_offloading_paper_document(trip.name)
	if not offloading_document:
		raise_offloading_paper_required()

	delivered_at = now_datetime()
	previous_delivery_datetime = trip.delivery_datetime
	trip.status = "DELIVERED"
	trip.driver_delivered_at = delivered_at
	if not flt(trip.delivered_quantity):
		trip.delivered_quantity = trip.loaded_quantity
	if not trip.delivery_datetime:
		trip.delivery_datetime = delivered_at
	trip.save(ignore_permissions=True)
	add_driver_trip_delivered_audit(
		trip.name,
		identity,
		"IN_TRANSIT",
		"DELIVERED",
		delivered_at,
		offloading_document.name,
	)
	if previous_delivery_datetime:
		trip.delivery_datetime = previous_delivery_datetime
	return build_mark_delivered_response(trip)


def fetch_driver_trips(driver: str, statuses: set[str]) -> list[frappe._dict]:
	fields = [
		"name",
		"trip_date",
		"status",
		"transport_job",
		"vehicle",
		"hired_vehicle",
		"loading_site",
		"unloading_site",
		"material",
		"planned_quantity",
		"loaded_quantity",
		"delivered_quantity",
		"loading_datetime",
		"delivery_datetime",
		"docstatus",
		"modified",
	]
	meta = frappe.get_meta("Transport Trip")
	fields.extend(fieldname for fieldname in PORTAL_OPTIONAL_FIELDS if meta.has_field(fieldname))

	return frappe.get_all(
		"Transport Trip",
		filters={"driver": driver, "status": ["in", sorted(statuses)]},
		fields=fields,
		limit_page_length=0,
	)


def fetch_trip_detail(trip_id: str) -> frappe._dict | None:
	fields = [
		"name",
		"trip_date",
		"status",
		"transport_job",
		"driver",
		"vehicle",
		"hired_vehicle",
		"loading_site",
		"unloading_site",
		"material",
		"planned_quantity",
		"loaded_quantity",
		"delivered_quantity",
		"uom",
		"loading_datetime",
		"driver_started_at",
		"driver_delivered_at",
		"delivery_datetime",
		"docstatus",
		"modified",
	]
	meta = frappe.get_meta("Transport Trip")
	fields.extend(fieldname for fieldname in PORTAL_OPTIONAL_FIELDS if meta.has_field(fieldname))
	return frappe.db.get_value("Transport Trip", trip_id, fields, as_dict=True)


def serialize_trip(trip: frappe._dict) -> dict:
	job = get_job_details(trip.transport_job)
	return {
		"trip_id": trip.name,
		"trip_date": format_value(trip.trip_date),
		"status": trip.status,
		"driver_portal_status": trip.get("driver_portal_status"),
		"transport_job": trip.transport_job,
		"truck": trip.vehicle,
		"hired_vehicle": trip.hired_vehicle,
		"loading_location": trip.loading_site,
		"unloading_location": trip.unloading_site,
		"material": trip.material,
		"quantity": get_billable_quantity(trip),
		"customer": job.get("customer"),
		"loading_datetime": format_value(trip.loading_datetime),
		"delivery_datetime": format_value(trip.delivery_datetime),
		"document_status": trip.get("document_status"),
		"loading_paper_status": trip.get("loading_paper_status"),
		"offloading_paper_status": trip.get("offloading_paper_status"),
		"toll_document_count": get_toll_document_count(trip.name),
		"documents_pending_review": trip.get("documents_pending_review"),
		"ai_review_status": trip.get("ai_review_status"),
	}


def serialize_trip_detail(trip: frappe._dict) -> dict:
	job = get_job_details(trip.transport_job)
	loading_stops = get_trip_loading_stops(trip.name)
	location_names = [trip.loading_site, trip.unloading_site]
	location_names.extend(stop.loading_location for stop in loading_stops)
	locations = get_location_details(location_names)
	customer = get_customer_display(job.get("customer"))
	material = get_material_display(trip.material)
	truck = get_truck_display(trip.vehicle)
	hired_vehicle = get_hired_vehicle_display(trip.hired_vehicle)
	return {
		"trip_id": trip.name,
		"trip_date": format_value(trip.trip_date),
		"status": trip.status,
		"transport_job": trip.transport_job,
		"customer": customer,
		"material": material,
		"quantity": get_billable_quantity(trip),
		"uom": trip.uom,
		"loading_location": get_location_display(trip.loading_site, locations),
		"loading_area_zone": get_location_area_zone(trip.loading_site, locations),
		"loading_stops": serialize_loading_stops(loading_stops, locations),
		"unloading_location": get_location_display(trip.unloading_site, locations),
		"unloading_area_zone": get_location_area_zone(trip.unloading_site, locations),
		"truck": truck,
		"hired_vehicle": hired_vehicle,
		"loading_datetime": format_value(trip.loading_datetime),
		"delivery_datetime": format_value(trip.delivery_datetime),
		"driver_started_at": format_value(trip.get("driver_started_at")),
		"driver_delivered_at": format_value(trip.get("driver_delivered_at")),
	}


def get_trip_loading_stops(trip_name: str) -> list[frappe._dict]:
	return frappe.get_all(
		"Transport Loading Stop",
		filters={
			"parenttype": "Transport Trip",
			"parentfield": "loading_stops",
			"parent": trip_name,
		},
		fields=["idx", "loading_location", "planned_quantity", "notes"],
		order_by="idx asc",
	)


def get_job_details(job_name: str | None) -> frappe._dict:
	if not job_name:
		return frappe._dict()
	return (
		frappe.db.get_value("Transport Job", job_name, ["customer"], as_dict=True)
		or frappe._dict()
	)


def get_customer_display(customer: str | None) -> str | None:
	if not customer:
		return None
	return frappe.db.get_value("Customer", customer, "customer_name") or customer


def get_material_display(material: str | None) -> str | None:
	if not material:
		return None
	return frappe.db.get_value("Cargo Types", material, "cargo_name") or material


def get_truck_display(truck: str | None) -> str | None:
	if not truck:
		return None
	return frappe.db.get_value("Truck", truck, "truck_number") or truck


def get_hired_vehicle_display(hired_vehicle: str | None) -> str | None:
	if not hired_vehicle:
		return None
	return frappe.db.get_value("Hired Vehicle", hired_vehicle, "plate_number") or hired_vehicle


def get_location_details(location_names: list[str | None]) -> dict[str, frappe._dict]:
	names = [name for name in location_names if name]
	if not names:
		return {}
	rows = frappe.get_all(
		"Transport Location",
		filters={"name": ["in", names]},
		fields=["name", "location", "area_zone"],
		limit_page_length=0,
	)
	return {row.name: row for row in rows}


def get_location_display(location: str | None, locations: dict[str, frappe._dict]) -> str | None:
	if not location:
		return None
	row = locations.get(location) or frappe._dict()
	return row.get("location") or location


def get_location_area_zone(location: str | None, locations: dict[str, frappe._dict]) -> str | None:
	if not location:
		return None
	row = locations.get(location) or frappe._dict()
	return row.get("area_zone")


def get_billable_quantity(trip: frappe._dict) -> float:
	for fieldname in ("delivered_quantity", "loaded_quantity", "planned_quantity"):
		value = flt(trip.get(fieldname))
		if value:
			return value
	return 0


def get_toll_document_count(trip_name: str) -> int:
	return frappe.db.count(
		"Transport Trip Document",
		{
			"transport_trip": trip_name,
			"document_type": ["in", ["ABER_TOLL", "SHARJAH_TOLL", "FNRC_RECEIPT"]],
		},
	)


def get_document_summary(trip: frappe._dict) -> dict:
	required_documents = get_required_driver_documents(trip)
	return get_trip_document_summary(trip, required_documents)


def get_required_driver_documents(trip: frappe._dict) -> list[str]:
	required = ["LOADING_PAPER"]
	for charge_type in get_route_dependent_charge_types(trip):
		document_type = CHARGE_DOCUMENT_TYPES.get(charge_type)
		if document_type and document_type not in required:
			required.append(document_type)
	required.append("OFFLOADING_PAPER")
	return required


def get_route_dependent_charge_types(trip: frappe._dict) -> list[str]:
	try:
		rows = calculate_transport_trip_charges(trip)
	except Exception:
		# Charge rules are operational billing config, not a blocker for V1 trip
		# detail. Fall back to mandatory loading/offloading papers.
		return []
	return [row.get("charge_type") for row in rows if row.get("charge_type")]


def get_allowed_driver_actions(status: str | None) -> list[str]:
	if status == "ASSIGNED":
		return ["START_TRIP"]
	if status == "IN_TRANSIT":
		return ["MARK_DELIVERED"]
	return []


def get_driver_delivery_requirements(trip) -> dict:
	offloading_document = get_offloading_paper_document(trip.name)
	can_mark_delivered = bool(trip.status == "IN_TRANSIT" and offloading_document)
	blocking_reason = None
	if trip.status == "IN_TRANSIT" and not offloading_document:
		blocking_reason = "OFFLOADING_PAPER_REQUIRED"
	return {
		"offloading_paper_uploaded": bool(offloading_document),
		"can_mark_delivered": can_mark_delivered,
		"blocking_reason": blocking_reason,
	}


def get_driver_trip_summary(driver: str) -> dict:
	rows = frappe.get_all(
		"Transport Trip",
		filters={"driver": driver},
		fields=["status"],
		limit_page_length=0,
	)
	return {
		"active": sum(1 for row in rows if row.status in ACTIVE_STATUSES),
		"upcoming": sum(1 for row in rows if row.status in UPCOMING_STATUSES),
		"completed": sum(1 for row in rows if row.status in COMPLETED_STATUSES),
	}


def normalize_view(view) -> str:
	view = (str(view or "").strip().lower() or "default")
	if view in {"active", "upcoming", "completed", "all"}:
		return view
	return "default"


def get_statuses_for_view(view: str) -> set[str]:
	if view == "active":
		return ACTIVE_STATUSES
	if view == "upcoming":
		return UPCOMING_STATUSES
	if view == "completed":
		return COMPLETED_STATUSES
	if view == "all":
		return ALL_STATUSES
	return DEFAULT_STATUSES


def normalize_limit(limit) -> int:
	limit = cint(limit) or DEFAULT_LIMIT
	if limit < 1:
		return DEFAULT_LIMIT
	return min(limit, MAX_LIMIT)


def normalize_offset(offset) -> int:
	offset = cint(offset)
	return max(offset, 0)


def trip_sort_key(trip: frappe._dict):
	rank = get_status_rank(trip.status)
	if trip.status in COMPLETED_STATUSES:
		return (rank, -timestamp(trip.delivery_datetime or trip.modified), trip.name)
	return (rank, timestamp(trip.trip_date or trip.modified), trip.name)


def get_status_rank(status: str) -> int:
	if status in ACTIVE_STATUSES:
		return 0
	if status in UPCOMING_STATUSES:
		return 1
	if status in COMPLETED_STATUSES:
		return 2
	if status in CANCELLED_STATUSES:
		return 3
	return 4


def timestamp(value) -> float:
	if not value:
		return 0
	if isinstance(value, datetime):
		return value.timestamp()
	if isinstance(value, date):
		return datetime.combine(value, datetime.min.time()).timestamp()
	return get_datetime(value).timestamp()


def format_value(value):
	if isinstance(value, datetime):
		return value.isoformat(sep=" ")
	if isinstance(value, date):
		return value.isoformat()
	return value


def raise_trip_not_found() -> None:
	frappe.local.response["http_status_code"] = 404
	frappe.throw(_("Trip not found or not permitted."), frappe.PermissionError)


def raise_invalid_start_state(status: str | None) -> None:
	frappe.local.response["http_status_code"] = 417
	frappe.throw(_("Trip cannot be started from status {0}.").format(status or "-"), frappe.ValidationError)


def raise_invalid_delivery_state(status: str | None) -> None:
	frappe.local.response["http_status_code"] = 417
	frappe.throw(_("Trip cannot be marked delivered from status {0}.").format(status or "-"), frappe.ValidationError)


def raise_offloading_paper_required() -> None:
	frappe.local.response["http_status_code"] = 417
	frappe.local.response["error_code"] = "OFFLOADING_PAPER_REQUIRED"
	frappe.throw(
		_("Upload the Offloading Paper before marking this trip as delivered."),
		frappe.ValidationError,
	)


def lock_trip_for_update(trip_id: str) -> None:
	rows = frappe.db.sql(
		"""
		select name
		from `tabTransport Trip`
		where name = %s
		for update
		""",
		trip_id,
		as_dict=True,
	)
	if not rows:
		raise_trip_not_found()


def build_start_trip_response(trip, already_started: bool = False) -> dict:
	return {
		"ok": True,
		"already_started": already_started,
		"trip": {
			"trip_id": trip.name,
			"status": trip.status,
			"driver_started_at": format_value(trip.get("driver_started_at")),
		},
		"allowed_actions": get_allowed_driver_actions(trip.status),
	}


def build_mark_delivered_response(trip, already_delivered: bool = False) -> dict:
	return {
		"ok": True,
		"already_delivered": already_delivered,
		"trip": {
			"trip_id": trip.name,
			"status": trip.status,
			"driver_delivered_at": format_value(trip.get("driver_delivered_at")),
		},
		"allowed_actions": get_allowed_driver_actions(trip.status),
	}


def get_offloading_paper_document(trip_name: str):
	return frappe.db.get_value(
		"Transport Trip Document",
		{
			"transport_trip": trip_name,
			"document_type": "OFFLOADING_PAPER",
		},
		["name", "verification_status", "ai_status"],
		as_dict=True,
	)


def add_driver_trip_started_audit(trip_name: str, identity: frappe._dict, previous_status: str, new_status: str, started_at) -> None:
	trip = frappe.get_doc("Transport Trip", trip_name)
	trip.add_comment(
		"Info",
		(
			"DRIVER_TRIP_STARTED<br>"
			f"Source: DRIVER_PORTAL<br>"
			f"Driver: {identity.truck_driver}<br>"
			f"Employee: {identity.employee}<br>"
			f"Previous Status: {previous_status}<br>"
			f"New Status: {new_status}<br>"
			f"Started At: {format_value(started_at)}"
		),
	)


def add_driver_trip_delivered_audit(
	trip_name: str,
	identity: frappe._dict,
	previous_status: str,
	new_status: str,
	delivered_at,
	offloading_document: str,
) -> None:
	trip = frappe.get_doc("Transport Trip", trip_name)
	trip.add_comment(
		"Info",
		(
			"DRIVER_TRIP_DELIVERED<br>"
			f"Source: DRIVER_PORTAL<br>"
			f"Driver: {identity.truck_driver}<br>"
			f"Employee: {identity.employee}<br>"
			f"Previous Status: {previous_status}<br>"
			f"New Status: {new_status}<br>"
			f"Delivered At: {format_value(delivered_at)}<br>"
			f"Offloading Paper: {offloading_document}"
		),
	)
