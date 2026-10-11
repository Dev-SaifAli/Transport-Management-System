"""Dashboard data providers for AL RANA TMS operational pages."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import today

BRAND_NAME = "AL RANA TRANSPORT LLC"
ACTIVE_TRIP_LIMIT = 10
ATTENTION_TRIP_LIMIT = 10
ACTIVE_TRIP_EXCLUDED_STATUSES = ("CLOSED", "CANCELLED")
ATTENTION_STATUSES = ("EXCEPTION", "DELIVERED")


@frappe.whitelist()
def get_trip_operations_dashboard():
	"""Return the Trip Data Entry operational dashboard payload."""
	if not frappe.has_permission("Transport Trip", ptype="read"):
		frappe.throw(_("You do not have permission to view Transport Trip dashboard data."), frappe.PermissionError)

	today_date = today()
	active_trips = get_active_trips()
	attention_trips = get_attention_trips()

	return {
		"brand": BRAND_NAME,
		"today": today_date,
		"user": {
			"full_name": frappe.utils.get_fullname(frappe.session.user),
		},
		"permissions": get_trip_dashboard_permissions(),
		"kpis": {
			"today": count_trips({"trip_date": today_date}),
			"planned": count_trips({"status": "PLANNED"}),
			"in_transit": count_trips({"status": "IN_TRANSIT"}),
			"pod_pending": count_trips({"status": "DELIVERED"}),
		},
		"active_trips": active_trips,
		"attention_trips": attention_trips,
		"limits": {
			"active_trips": ACTIVE_TRIP_LIMIT,
			"attention_trips": ATTENTION_TRIP_LIMIT,
		},
	}


def get_trip_dashboard_permissions():
	return {
		"can_create_trip": frappe.has_permission("Transport Trip", ptype="create"),
		"can_read_trip": frappe.has_permission("Transport Trip", ptype="read"),
		"can_read_job": frappe.has_permission("Transport Job", ptype="read"),
	}


def count_trips(filters):
	rows = frappe.get_list(
		"Transport Trip",
		filters=filters,
		fields=[{"COUNT": "name", "as": "count"}],
		limit=1,
	)
	if not rows:
		return 0
	return frappe.utils.cint(rows[0].get("count"))


def get_active_trips():
	trips = frappe.get_list(
		"Transport Trip",
		filters={"status": ["not in", ACTIVE_TRIP_EXCLUDED_STATUSES]},
		fields=[
			"name",
			"transport_job",
			"loading_site",
			"unloading_site",
			"execution_source",
			"vehicle",
			"hired_vehicle",
			"driver",
			"hired_driver",
			"status",
			"modified",
		],
		order_by="modified desc",
		limit=ACTIVE_TRIP_LIMIT,
	)
	return build_trip_rows(trips)


def get_attention_trips():
	trips = frappe.get_list(
		"Transport Trip",
		filters={"status": ["in", ATTENTION_STATUSES]},
		fields=[
			"name",
			"transport_job",
			"loading_site",
			"unloading_site",
			"execution_source",
			"vehicle",
			"hired_vehicle",
			"driver",
			"hired_driver",
			"status",
			"modified",
		],
		order_by="modified desc",
		limit=ATTENTION_TRIP_LIMIT,
	)
	return build_trip_rows(trips, include_issue=True)


def build_trip_rows(trips, include_issue=False):
	job_map = get_job_customer_map(trips)
	rows = []
	for trip in trips:
		row = {
			"trip": trip.name,
			"transport_job": trip.transport_job,
			"customer": job_map.get(trip.transport_job),
			"loading": trip.loading_site,
			"unloading": trip.unloading_site,
			"route": build_route(trip.loading_site, trip.unloading_site),
			"vehicle": get_effective_vehicle(trip),
			"driver": get_effective_driver(trip),
			"status": trip.status,
			"updated": trip.modified,
		}
		if include_issue:
			row["issue"] = get_attention_issue(trip.status)
		rows.append(row)
	return rows


def get_job_customer_map(trips):
	job_names = sorted({trip.transport_job for trip in trips if trip.transport_job})
	if not job_names or not frappe.has_permission("Transport Job", ptype="read"):
		return {}

	jobs = frappe.get_list(
		"Transport Job",
		filters={"name": ["in", job_names]},
		fields=["name", "customer"],
		limit=len(job_names),
	)
	return {job.name: job.customer for job in jobs}


def build_route(loading, unloading):
	return " -> ".join(part for part in (loading, unloading) if part)


def get_effective_vehicle(trip):
	if trip.execution_source == "HIRED":
		return trip.hired_vehicle
	return trip.vehicle


def get_effective_driver(trip):
	if trip.execution_source == "HIRED":
		return trip.hired_driver
	return trip.driver


def get_attention_issue(status):
	if status == "EXCEPTION":
		return _("Exception")
	if status == "DELIVERED":
		return _("POD Pending")
	return status
