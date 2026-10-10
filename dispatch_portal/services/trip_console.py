"""Dispatcher console services.

Serialisation helpers shared by the whitelisted API layer.  Everything reads from
the real TMS DocTypes - no transportation entity is duplicated here.
"""

from __future__ import annotations

import frappe
from frappe.utils import cint, flt

TRIP_LIST_FIELDS = (
	"name",
	"transport_job",
	"trip_date",
	"status",
	"loading_site",
	"loading_stops",
	"unloading_site",
	"material",
	"planned_quantity",
	"uom",
	"execution_source",
	"vehicle",
	"driver",
	"transporter",
	"hired_vehicle",
	"hired_driver",
	"loaded_quantity",
	"loading_datetime",
	"driver_started_at",
	"delivered_quantity",
	"delivery_datetime",
	"driver_delivered_at",
	"gdn",
	"loading_no",
	"unloading_no",
	"pod_attachment",
	"pod_received_at",
	"transport_billing_status",
	"remarks",
	"modified",
)

TRIP_DETAIL_FIELDS = TRIP_LIST_FIELDS + (
	"actual_quantity",
	"toll_applicable",
	"rak_toll",
	"sharjah_toll",
	"fnrc_extra_charge",
	"transport_charges",
	"assignment_notification_status",
	"assignment_notified_at",
)

TRIP_ACTIVE_STATUSES = ("PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED")

DASHBOARD_STATUS_ORDER = (
	"PLANNED",
	"ASSIGNED",
	"LOADED",
	"IN_TRANSIT",
	"DELIVERED",
	"POD_RECEIVED",
	"EXCEPTION",
	"CLOSED",
	"CANCELLED",
)


def to_int(value, default=0):
	try:
		return cint(value)
	except (TypeError, ValueError):
		return default


def to_float(value, default=0.0):
	try:
		return flt(value, 6)
	except (TypeError, ValueError):
		return default


def normalize_limit(value, default=25, maximum=200):
	limit = to_int(value, default)
	if limit <= 0:
		limit = default
	return min(limit, maximum)


def normalize_offset(value):
	return max(to_int(value, 0), 0)


def trip_filters(filters=None) -> dict:
	"""Build a Transport Trip filter dict from console filter parameters."""
	filters = frappe._dict(filters or {})
	result = frappe._dict()

	if filters.status:
		result.status = filters.status
	if filters.execution_source:
		result.execution_source = filters.execution_source
	if filters.transport_job:
		result.transport_job = filters.transport_job
	if filters.vehicle:
		result.vehicle = filters.vehicle
	if filters.driver:
		result.driver = filters.driver
	if filters.material:
		result.material = filters.material
	if filters.customer:
		jobs = frappe.get_all(
			"Transport Job",
			filters={"customer": filters.customer},
			pluck="name",
			limit=500,
		)
		result.transport_job = ["in", jobs] if jobs else [""]

	from_date = filters.get("from_date") or filters.get("date_from")
	to_date = filters.get("to_date") or filters.get("date_to")
	if from_date and to_date:
		result.trip_date = ["between", [from_date, to_date]]
	elif from_date:
		result.trip_date = [">=", from_date]
	elif to_date:
		result.trip_date = ["<=", to_date]

	search = (filters.get("search") or "").strip()
	if search:
		result.name = ["like", f"%{search}%"]

	return result


def get_trip_count(filters=None, extra=None) -> int:
	query = dict(trip_filters(filters))
	if extra:
		query.update(extra)
	rows = frappe.get_list(
		"Transport Trip",
		filters=query,
		fields=[{"COUNT": "name", "as": "count"}],
		limit=1,
	)
	return to_int(rows[0].get("count")) if rows else 0


def list_trips(filters=None, start=0, page_length=25, order_by=None) -> list[dict]:
	query = trip_filters(filters)
	return frappe.get_list(
		"Transport Trip",
		filters=query,
		fields=list(TRIP_LIST_FIELDS),
		order_by=order_by or "modified desc",
		limit_start=normalize_offset(start),
		limit_page_length=normalize_limit(page_length),
	)


def get_trip_doc(trip_id):
	if not trip_id:
		frappe.throw("Transport Trip is required.")
	return frappe.get_doc("Transport Trip", trip_id)


def serialize_trip_summary(trip) -> dict:
	"""Compact row used by the dashboard board, trips table and map markers."""
	return {
		"trip": trip.name,
		"transport_job": trip.get("transport_job"),
		"customer": get_customer_for_job(trip.get("transport_job")),
		"trip_date": str(trip.get("trip_date") or ""),
		"status": trip.get("status"),
		"loading_site": trip.get("loading_site"),
		"unloading_site": trip.get("unloading_site"),
		"route": build_route(trip.get("loading_site"), trip.get("unloading_site")),
		"material": trip.get("material"),
		"planned_quantity": to_float(trip.get("planned_quantity")),
		"uom": trip.get("uom"),
		"execution_source": trip.get("execution_source"),
		"vehicle": get_effective_vehicle(trip),
		"driver": get_effective_driver(trip),
		"driver_started_at": format_datetime(trip.get("driver_started_at")),
		"loading_datetime": format_datetime(trip.get("loading_datetime")),
		"delivered_quantity": to_float(trip.get("delivered_quantity")),
		"delivery_datetime": format_datetime(trip.get("delivery_datetime")),
		"gdn": trip.get("gdn"),
		"pod_attachment": trip.get("pod_attachment"),
		"pod_received_at": format_datetime(trip.get("pod_received_at")),
		"transport_billing_status": trip.get("transport_billing_status"),
		"modified": format_datetime(trip.get("modified")),
	}


def serialize_trip_detail(trip) -> dict:
	row = serialize_trip_summary(trip)
	row.update(
		{
			"actual_quantity": to_float(trip.get("actual_quantity")),
			"loaded_quantity": to_float(trip.get("loaded_quantity")),
			"loading_no": trip.get("loading_no"),
			"unloading_no": trip.get("unloading_no"),
			"remarks": trip.get("remarks"),
			"transporter": trip.get("transporter"),
			"hired_vehicle": trip.get("hired_vehicle"),
			"hired_driver": trip.get("hired_driver"),
			"toll_applicable": trip.get("toll_applicable"),
			"rak_toll": to_float(trip.get("rak_toll")),
			"sharjah_toll": to_float(trip.get("sharjah_toll")),
			"fnrc_extra_charge": to_float(trip.get("fnrc_extra_charge")),
			"assignment_notification_status": trip.get("assignment_notification_status"),
			"assignment_notified_at": format_datetime(trip.get("assignment_notified_at")),
			"loading_stops": serialize_loading_stops(trip),
			"job": serialize_job(trip.get("transport_job")),
			"charges": serialize_charges(trip),
			"vehicle": trip.get("vehicle"),
			"driver": trip.get("driver"),
		}
	)
	return row


def serialize_loading_stops(trip) -> list[dict]:
	stops = []
	for row in trip.get("loading_stops") or []:
		stops.append(
			{
				"loading_location": row.get("loading_location"),
				"planned_quantity": to_float(row.get("planned_quantity")),
				"notes": row.get("notes"),
			}
		)
	return stops


def serialize_charges(trip) -> list[dict]:
	charges = []
	for row in trip.get("transport_charges") or []:
		charges.append(
			{
				"charge_type": row.get("charge_type"),
				"rate_basis": row.get("rate_basis"),
				"rate": to_float(row.get("rate")),
				"quantity": to_float(row.get("quantity")),
				"amount": to_float(row.get("amount")),
				"source": row.get("source"),
			}
		)
	return charges


def serialize_job(job_name) -> dict | None:
	if not job_name:
		return None
	if not frappe.has_permission("Transport Job", ptype="read"):
		return {"name": job_name}
	job = frappe.db.get_value(
		"Transport Job",
		job_name,
		[
			"name",
			"customer",
			"status",
			"loading_site",
			"unloading_site",
			"material",
			"requested_quantity",
			"uom",
			"requested_date",
			"customer_lpo_number",
			"do_number",
			"special_instructions",
			"billing_status",
		],
		as_dict=True,
	)
	if not job:
		return {"name": job_name}
	return {
		"name": job.name,
		"customer": job.customer,
		"status": job.status,
		"loading_site": job.loading_site,
		"unloading_site": job.unloading_site,
		"material": job.material,
		"requested_quantity": to_float(job.requested_quantity),
		"uom": job.uom,
		"requested_date": str(job.requested_date or ""),
		"customer_lpo_number": job.get("customer_lpo_number"),
		"do_number": job.get("do_number"),
		"special_instructions": job.get("special_instructions"),
		"billing_status": job.get("billing_status"),
	}


_JOB_CUSTOMER_CACHE: dict[str, str | None] = {}


def get_customer_for_job(job_name) -> str | None:
	if not job_name:
		return None
	if job_name not in _JOB_CUSTOMER_CACHE:
		_JOB_CUSTOMER_CACHE[job_name] = frappe.db.get_value("Transport Job", job_name, "customer")
	return _JOB_CUSTOMER_CACHE[job_name]


def clear_customer_cache() -> None:
	_JOB_CUSTOMER_CACHE.clear()


def build_route(loading, unloading) -> str:
	return " -> ".join(part for part in (loading, unloading) if part)


def get_effective_vehicle(trip) -> str | None:
	if trip.get("execution_source") == "HIRED":
		return trip.get("hired_vehicle") or trip.get("vehicle")
	return trip.get("vehicle") or trip.get("hired_vehicle")


def get_effective_driver(trip) -> str | None:
	if trip.get("execution_source") == "HIRED":
		return trip.get("hired_driver") or trip.get("driver")
	return trip.get("driver") or trip.get("hired_driver")


def format_datetime(value) -> str | None:
	if not value:
		return None
	return str(value)
