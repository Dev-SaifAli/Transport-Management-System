"""Dispatcher reports API."""

from __future__ import annotations

import frappe

from dispatch_portal.services.report_service import (
	get_driver_performance,
	get_pending_pod_trips,
	get_reports_overview,
	get_trip_report_rows,
)


@frappe.whitelist()
def get_reports(from_date=None, to_date=None):
	return get_reports_overview(from_date=from_date, to_date=to_date)


@frappe.whitelist()
def get_trip_report(from_date=None, to_date=None, limit=200):
	return {"rows": get_trip_report_rows(from_date=from_date, to_date=to_date, limit=limit)}


@frappe.whitelist()
def get_driver_report(from_date=None, to_date=None):
	return {"rows": get_driver_performance(from_date=from_date, to_date=to_date)}


@frappe.whitelist()
def get_pod_backlog(limit=50):
	return {"rows": get_pending_pod_trips(limit=limit)}
