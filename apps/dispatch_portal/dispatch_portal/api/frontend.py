"""Vue dispatch portal API facade.

These methods keep the /dispatch frontend on the same permission-aware data
sources as the native Desk console.  They only read TMS DocTypes and delegate
mutations to the existing verification API.
"""

from __future__ import annotations

import frappe
from frappe.utils import format_datetime, pretty_date, today

from dispatch_portal.services.dispatch_access import (
	require_console_access,
	require_verification_access,
)
from dispatch_portal.services.trip_console import (
	DASHBOARD_STATUS_ORDER,
	get_trip_doc,
	list_trips,
	normalize_limit,
	serialize_trip_detail,
	serialize_trip_summary,
	to_float,
	to_int,
)
from dispatch_portal.services.verification_service import (
	DOCUMENT_TYPE_LABELS,
	get_document_review,
)


STATUS_LABELS = {
	"PLANNED": "Planned",
	"ASSIGNED": "Assigned",
	"LOADED": "Loaded",
	"IN_TRANSIT": "In transit",
	"DELIVERED": "Delivered",
	"POD_RECEIVED": "POD pending",
	"EXCEPTION": "Exception",
	"CLOSED": "Closed",
	"CANCELLED": "Cancelled",
}

FRONTEND_STATUSES = ("Planned", "Assigned", "Loaded", "In transit", "Delivered", "POD pending", "Exception")
ACTIVE_STATUSES = ("PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT")
ATTENTION_STATUSES = ("EXCEPTION", "DELIVERED", "POD_RECEIVED")


@frappe.whitelist()
def get_dashboard_view():
	"""Complete dashboard payload for the Vue app."""
	require_console_access()
	trips = [
		serialize_frontend_trip(row)
		for row in list_trips(
			filters={"status": ["in", list(ACTIVE_STATUSES)]},
			page_length=25,
			order_by="modified desc",
		)
	]
	attention = get_attention_rows()
	verification = get_verification_rows(limit=8) if can_verify() else []
	kpis = get_kpis()
	return {
		"kpis": kpis,
		"statuses": list(FRONTEND_STATUSES),
		"pipeline": get_pipeline(),
		"trips": trips,
		"attention": attention,
		"verification": verification,
		"resources": {
			"available_trucks": kpis.get("available_trucks", 0),
			"active_drivers": kpis.get("active_drivers", 0),
		},
		"counts": {
			"live_trips": len(trips),
			"attention": len(attention),
			"verification": len(verification),
		},
	}


@frappe.whitelist()
def get_live_trips_view(filters=None, start=0, page_length=50):
	"""Live trips view with one permission-aware trip list call."""
	require_console_access()
	trips = list_trips(
		filters=frappe.parse_json(filters) if isinstance(filters, str) else filters,
		start=start,
		page_length=normalize_limit(page_length, default=50, maximum=200),
		order_by="modified desc",
	)
	return {
		"statuses": list(FRONTEND_STATUSES),
		"trips": [serialize_frontend_trip(row) for row in trips],
		"pipeline": get_pipeline(),
	}


@frappe.whitelist()
def get_attention_view():
	"""Trips requiring dispatcher attention."""
	require_console_access()
	items = get_attention_rows()
	return {"items": items, "count": len(items)}


@frappe.whitelist()
def get_verification_view(start=0, page_length=25):
	"""Verification queue shaped for the Vue card and drawer."""
	require_verification_access()
	documents = get_verification_rows(
		start=to_int(start),
		limit=normalize_limit(page_length, default=25, maximum=100),
	)
	return {"documents": documents, "count": len(documents)}


@frappe.whitelist()
def get_trip_view(trip_id):
	"""Single trip payload for deep-linked drawer routes."""
	require_console_access()
	trip = get_trip_doc(trip_id)
	return serialize_frontend_trip(serialize_trip_detail(trip))


def get_kpis() -> dict:
	today_date = today()
	return {
		"trips_today": count_doctype("Transport Trip", {"trip_date": today_date}),
		"planned": count_doctype("Transport Trip", {"status": "PLANNED"}),
		"assigned": count_doctype("Transport Trip", {"status": "ASSIGNED"}),
		"in_transit": count_doctype("Transport Trip", {"status": "IN_TRANSIT"}),
		"pod_pending": count_doctype("Transport Trip", {"status": ["in", ["DELIVERED", "POD_RECEIVED"]]}),
		"exception": count_doctype("Transport Trip", {"status": "EXCEPTION"}),
		"available_trucks": count_doctype("Truck", {"status": "Idle", "disabled": 0}),
		"active_drivers": count_doctype("Truck Driver", {"status": "Active"}),
	}


def get_pipeline() -> list[dict]:
	rows = frappe.get_list(
		"Transport Trip",
		fields=["status", {"COUNT": "name", "as": "count"}],
		group_by="status",
		limit_page_length=max(len(DASHBOARD_STATUS_ORDER), 1),
	)
	counts = {row.status: to_int(row.get("count")) for row in rows}
	pipeline = []
	for status in DASHBOARD_STATUS_ORDER:
		label = STATUS_LABELS.get(status, status.replace("_", " ").title())
		pipeline.append({"status": label, "source_status": status, "count": counts.get(status, 0)})
	return pipeline


def get_attention_rows() -> list[dict]:
	trips = list_trips(
		filters={"status": ["in", list(ATTENTION_STATUSES)]},
		page_length=25,
		order_by="modified desc",
	)
	return [serialize_frontend_trip(row, include_alert=True) for row in trips]


def get_verification_rows(start=0, limit=25) -> list[dict]:
	rows = frappe.get_list(
		"Transport Trip Document",
		filters={"verification_status": "PENDING_REVIEW"},
		fields=[
			"name",
			"transport_trip",
			"document_type",
			"file",
			"uploaded_at",
			"ai_confidence",
			"verification_status",
		],
		order_by="uploaded_at desc",
		limit_start=to_int(start),
		limit_page_length=normalize_limit(limit, default=25, maximum=100),
	)
	documents = []
	for row in rows:
		try:
			detail = get_document_review(row.name)
		except Exception:
			detail = {}
		documents.append(serialize_frontend_document(row, detail))
	return documents


def serialize_frontend_trip(trip, include_alert=False) -> dict:
	row = serialize_trip_summary(frappe._dict(trip)) if "trip" not in trip else dict(trip)
	status = STATUS_LABELS.get(row.get("status"), row.get("status") or "Planned")
	quantity = row.get("planned_quantity")
	if quantity not in (None, ""):
		quantity = "{0:g} {1}".format(to_float(quantity), row.get("uom") or "").strip()
	return {
		**row,
		"trip": row.get("trip") or row.get("name"),
		"status": status,
		"source_status": row.get("status"),
		"route": row.get("route") or build_route(row.get("loading_site"), row.get("unloading_site")),
		"vehicle": row.get("vehicle") or "Unassigned",
		"driver": row.get("driver") or "Unassigned",
		"customer": row.get("customer") or "",
		"eta": build_eta(row),
		"updated": pretty_date(row.get("modified")) if row.get("modified") else "",
		"quantity": quantity or "",
		"note": build_attention_note(row) if include_alert else row.get("remarks") or "",
	}


def serialize_frontend_document(row, detail=None) -> dict:
	detail = detail or {}
	document = detail.get("document") or {}
	candidates = detail.get("candidates") or []
	filename = (document.get("file") or row.get("file") or "").rsplit("/", 1)[-1]
	return {
		"id": row.name,
		"name": row.name,
		"trip": row.transport_trip,
		"type": DOCUMENT_TYPE_LABELS.get(row.document_type, row.document_type),
		"document_type": row.document_type,
		"filename": filename or row.name,
		"age": pretty_date(row.uploaded_at) if row.uploaded_at else "",
		"review": "Needs review",
		"confidence": to_int(row.ai_confidence),
		"fields": [
			{
				"label": candidate.get("label"),
				"value": candidate.get("extracted_value"),
				"expected": candidate.get("current_value"),
				"confidence": to_int(row.ai_confidence),
				"match": not bool(candidate.get("differs")),
				"extracted_field": candidate.get("extracted_field"),
				"can_write_trip": bool(candidate.get("can_write_trip")),
			}
			for candidate in candidates
		],
	}


def build_eta(row) -> str:
	if row.get("status") in ("DELIVERED", "POD_RECEIVED"):
		return "Delivered"
	if row.get("delivery_datetime"):
		return format_datetime(row.get("delivery_datetime"), "HH:mm")
	if row.get("driver_started_at"):
		return "In progress"
	return "-"


def build_attention_note(row) -> str:
	if row.get("status") == "EXCEPTION":
		return row.get("remarks") or "Trip flagged as an exception - immediate dispatcher review required."
	if row.get("status") == "DELIVERED" and not row.get("pod_attachment"):
		return "Delivery complete. Proof of delivery is still outstanding."
	if row.get("status") == "POD_RECEIVED" and row.get("transport_billing_status") == "Not Billed":
		return "POD received but trip is not billed yet."
	return row.get("remarks") or ""


def build_route(loading, unloading) -> str:
	return " -> ".join(part for part in (loading, unloading) if part)


def count_doctype(doctype: str, filters=None) -> int:
	rows = frappe.get_list(
		doctype,
		filters=filters or {},
		fields=[{"COUNT": "name", "as": "count"}],
		limit_page_length=1,
	)
	return to_int(rows[0].get("count")) if rows else 0


def can_verify() -> bool:
	try:
		require_verification_access()
		return True
	except Exception:
		return False
