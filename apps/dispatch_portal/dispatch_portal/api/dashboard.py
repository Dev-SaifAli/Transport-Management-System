"""Dispatcher dashboard API."""

from __future__ import annotations

import frappe

from dispatch_portal.services.dispatch_access import require_console_access
from dispatch_portal.services.report_service import get_pending_pod_trips
from dispatch_portal.services.trip_console import (
	DASHBOARD_STATUS_ORDER,
	list_trips,
	serialize_trip_summary,
	to_int,
)
from dispatch_portal.services.verification_service import get_review_summary


@frappe.whitelist()
def get_dashboard():
	"""KPI board, live trip board and alert feed for the dispatcher console."""
	require_console_access()

	from frappe.utils import today

	return {
		"kpis": get_kpis(),
		"status_breakdown": get_status_breakdown(),
		"active_trips": get_active_trips(),
		"attention_trips": get_attention_trips(),
		"pending_pod": get_pending_pod_trips(),
		"verification": get_verification_backlog(),
	}


def get_kpis() -> dict:
	today_date = today_date_value()
	return {
		"trips_today": count_trips({"trip_date": today_date}),
		"planned": count_trips({"status": "PLANNED"}),
		"assigned": count_trips({"status": "ASSIGNED"}),
		"in_transit": count_trips({"status": "IN_TRANSIT"}),
		"delivered": count_trips({"status": "DELIVERED"}),
		"pod_pending": count_trips({"status": "DELIVERED"}),
		"exception": count_trips({"status": "EXCEPTION"}),
		"active_jobs": count_doctype("Transport Job", filters={"status": ["in", ["Ready", "In Progress"]]}),
		"available_trucks": count_doctype("Truck", filters={"status": "Idle", "disabled": 0}),
		"active_drivers": count_doctype("Truck Driver", filters={"status": "Active"}),
	}


def get_status_breakdown() -> list[dict]:
	rows = frappe.get_all(
		"Transport Trip",
		fields=["status", {"COUNT": "name", "as": "count"}],
		group_by="status",
		limit_page_length=max(len(DASHBOARD_STATUS_ORDER), 1),
	)
	counts = {row.status: to_int(row.get("count")) for row in rows}
	return [
		{"status": status, "count": counts.get(status, 0)}
		for status in DASHBOARD_STATUS_ORDER
		if counts.get(status, 0)
	]


def get_active_trips() -> list[dict]:
	trips = list_trips(
		filters={"status": ["in", ["PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT"]]},
		page_length=12,
		order_by="modified desc",
	)
	return [serialize_trip_summary(trip) for trip in trips]


def get_attention_trips() -> list[dict]:
	trips = list_trips(
		filters={"status": ["in", ["EXCEPTION", "DELIVERED", "POD_RECEIVED"]]},
		page_length=12,
		order_by="modified desc",
	)
	rows = [serialize_trip_summary(trip) for trip in trips]
	for row, trip in zip(rows, trips):
		row["alert"] = build_alert(row)
	return rows


def build_alert(row) -> str | None:
	if row["status"] == "EXCEPTION":
		return "Trip flagged as an exception - immediate dispatcher review required."
	if row["status"] == "DELIVERED" and not row["pod_attachment"]:
		return "Delivered without a POD attachment."
	if row["status"] == "POD_RECEIVED" and row["transport_billing_status"] == "Not Billed":
		return "POD received but the trip is not billed yet."
	return None


def get_verification_backlog() -> dict:
	try:
		return get_review_summary()
	except frappe.PermissionError:
		return {"pending_review": 0, "approved": 0, "rejected": 0, "by_document_type": {}}


def count_trips(filters) -> int:
	return count_doctype("Transport Trip", filters=filters)


def count_doctype(doctype, filters=None) -> int:
	try:
		return to_int(frappe.db.count(doctype, filters or {}))
	except Exception:
		return 0


def today_date_value():
	from frappe.utils import today

	return today()
