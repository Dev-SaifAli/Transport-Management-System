"""Reporting aggregates for the AL RANA Dispatch console.

Reports read the real TMS DocTypes only.  Amounts are indicative operational
rollups; billing totals remain owned by ``transport_management`` and ERPNext.
"""

from __future__ import annotations

from datetime import date, timedelta

import frappe
from frappe.utils import add_days, getdate, today

from dispatch_portal.services.dispatch_access import require_console_access
from dispatch_portal.services.trip_console import to_float

DEFAULT_RANGE_DAYS = 30


def resolve_range(from_date=None, to_date=None) -> tuple[date, date]:
	end = getdate(to_date) if to_date else getdate(today())
	start = getdate(from_date) if from_date else add_days(end, -DEFAULT_RANGE_DAYS)
	if start > end:
		start, end = end, start
	return start, end


def trip_range_filter(from_date=None, to_date=None) -> dict:
	start, end = resolve_range(from_date, to_date)
	return {"trip_date": ["between", [start, end]]}


def get_reports_overview(from_date=None, to_date=None) -> dict:
	"""Console Reports section payload."""
	require_console_access()
	start, end = resolve_range(from_date, to_date)
	range_filter = {"trip_date": ["between", [start, end]]}

	return {
		"range": {"from": str(start), "to": str(end)},
		"trips_by_status": count_by("Transport Trip", "status", range_filter),
		"trips_by_execution_source": count_by(
			"Transport Trip", "execution_source", range_filter
		),
		"trips_by_material": count_by("Transport Trip", "material", range_filter),
		"trips_by_customer": trips_by_customer(range_filter),
		"quantity_delivered": quantity_totals(range_filter),
		"document_verification": verification_totals(range_filter),
		"fleet_utilization": fleet_utilization(range_filter),
		"daily_trip_volume": daily_trip_volume(start, end),
	}


def count_by(doctype, fieldname, filters=None, limit=20) -> list[dict]:
	rows = frappe.get_all(
		doctype,
		filters=filters or {},
		fields=[fieldname, {"COUNT": "name", "as": "count"}],
		group_by=fieldname,
		order_by="count desc",
		limit_page_length=limit,
	)
	return [
		{"key": row.get(fieldname) or "Unknown", "label": row.get(fieldname) or "Unknown", "count": int(row.count or 0)}
		for row in rows
	]


def trips_by_customer(range_filter) -> list[dict]:
	rows = frappe.get_all(
		"Transport Trip",
		filters=range_filter,
		fields=["transport_job", {"COUNT": "name", "as": "count"}],
		group_by="transport_job",
		limit_page_length=500,
	)
	job_names = [row.transport_job for row in rows if row.transport_job]
	customers = {}
	if job_names:
		job_rows = frappe.get_all(
			"Transport Job",
			filters={"name": ["in", job_names]},
			fields=["name", "customer"],
			limit_page_length=max(len(job_names), 1),
		)
		customers = {row.name: row.customer for row in job_rows}

	totals: dict[str, int] = {}
	for row in rows:
		customer = customers.get(row.transport_job) or "Unknown"
		totals[customer] = totals.get(customer, 0) + int(row.count or 0)

	return [
		{"key": key, "label": key, "count": value}
		for key, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:20]
	]


def quantity_totals(range_filter) -> dict:
	rows = frappe.get_all(
		"Transport Trip",
		filters=range_filter,
		fields=[
			{"SUM": "planned_quantity", "as": "planned"},
			{"SUM": "loaded_quantity", "as": "loaded"},
			{"SUM": "delivered_quantity", "as": "delivered"},
			{"SUM": "actual_quantity", "as": "actual"},
		],
		limit_page_length=1,
	)
	row = rows[0] if rows else frappe._dict()
	return {
		"planned": to_float(row.get("planned")),
		"loaded": to_float(row.get("loaded")),
		"delivered": to_float(row.get("delivered")),
		"actual": to_float(row.get("actual")),
	}


def verification_totals(range_filter) -> dict:
	rows = frappe.get_all(
		"Transport Trip Document",
		filters={"verification_status": ["!=", ""]},
		fields=["verification_status", {"COUNT": "name", "as": "count"}],
		group_by="verification_status",
	)
	totals = {row.verification_status: int(row.count or 0) for row in rows}
	return {
		"pending_review": totals.get("PENDING_REVIEW", 0),
		"approved": totals.get("APPROVED", 0),
		"rejected": totals.get("REJECTED", 0),
	}


def fleet_utilization(range_filter) -> dict:
	rows = frappe.get_all(
		"Transport Trip",
		filters=range_filter,
		fields=["vehicle", {"COUNT": "name", "as": "count"}],
		group_by="vehicle",
		limit_page_length=1000,
	)
	totals = {row.vehicle or "Unassigned": int(row.count or 0) for row in rows}
	return {
		"trips_per_vehicle": [
			{"vehicle": key, "trips": value}
			for key, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:20]
		]
	}


def daily_trip_volume(start, end) -> list[dict]:
	days = (end - start).days + 1
	if days <= 0 or days > 92:
		days = min(max(days, 1), 92)
	rows = frappe.get_all(
		"Transport Trip",
		filters={"trip_date": ["between", [add_days(end, -(days - 1)), end]]},
		fields=["trip_date", {"COUNT": "name", "as": "count"}],
		group_by="trip_date",
		limit_page_length=days,
	)
	counts = {str(row.trip_date): int(row.count or 0) for row in rows}
	series = []
	for offset in range(days - 1, -1, -1):
		day = add_days(end, -offset)
		series.append({"date": str(day), "count": counts.get(str(day), 0)})
	return series


def get_driver_performance(from_date=None, to_date=None) -> list[dict]:
	require_console_access()
	range_filter = trip_range_filter(from_date, to_date)
	rows = frappe.get_all(
		"Transport Trip",
		filters=range_filter,
		fields=[
			"driver",
			{"COUNT": "name", "as": "trips"},
			{"SUM": "delivered_quantity", "as": "delivered"},
		],
		group_by="driver",
		order_by="trips desc",
		limit_page_length=50,
	)
	return [
		{
			"driver": row.driver or "Unassigned",
			"trips": int(row.trips or 0),
			"delivered_quantity": to_float(row.get("delivered")),
		}
		for row in rows
	]


def get_trip_report_rows(from_date=None, to_date=None, limit=200) -> list[dict]:
	require_console_access()
	range_filter = trip_range_filter(from_date, to_date)
	trips = frappe.get_all(
		"Transport Trip",
		filters=range_filter,
		fields=[
			"name",
			"trip_date",
			"status",
			"transport_job",
			"loading_site",
			"unloading_site",
			"material",
			"planned_quantity",
			"delivered_quantity",
			"vehicle",
			"driver",
			"hired_vehicle",
			"hired_driver",
			"execution_source",
			"transport_billing_status",
		],
		order_by="trip_date desc",
		limit_page_length=limit,
	)
	return [serialize_report_row(trip) for trip in trips]


def serialize_report_row(trip) -> dict:
	return {
		"trip": trip.name,
		"trip_date": str(trip.get("trip_date") or ""),
		"status": trip.get("status"),
		"transport_job": trip.get("transport_job"),
		"customer": frappe.db.get_value("Transport Job", trip.get("transport_job"), "customer")
		if trip.get("transport_job")
		else None,
		"loading_site": trip.get("loading_site"),
		"unloading_site": trip.get("unloading_site"),
		"material": trip.get("material"),
		"planned_quantity": to_float(trip.get("planned_quantity")),
		"delivered_quantity": to_float(trip.get("delivered_quantity")),
		"vehicle": trip.get("vehicle") or trip.get("hired_vehicle"),
		"driver": trip.get("driver") or trip.get("hired_driver"),
		"execution_source": trip.get("execution_source"),
		"transport_billing_status": trip.get("transport_billing_status"),
	}


def get_pending_pod_trips(limit=50) -> list[dict]:
	require_console_access()
	trips = frappe.get_all(
		"Transport Trip",
		filters={"status": "DELIVERED"},
		fields=["name", "transport_job", "delivered_quantity", "delivery_datetime", "vehicle", "driver"],
		order_by="delivery_datetime asc",
		limit_page_length=limit,
	)
	return [
		{
			"trip": row.name,
			"transport_job": row.transport_job,
			"delivered_quantity": to_float(row.get("delivered_quantity")),
			"delivery_datetime": str(row.get("delivery_datetime") or ""),
			"vehicle": row.vehicle,
			"driver": row.driver,
		}
		for row in trips
	]
