"""Dispatcher verification service for Transport Trip Documents.

AI extraction is treated as **advice only**.  The service exposes a strictly
allow-listed set of candidate fields and only writes the ones the verifier
explicitly accepts, so an extraction can never silently overwrite authoritative
trip data.  Fields that decide the trip itself - status, quantities, rates,
vehicle, driver, material and locations - are never writable from here.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from dispatch_portal.services.dispatch_access import is_verifier, require_verification_access
from frappe.exceptions import PermissionError as FrappePermissionError

DOCUMENT_TYPE_LABELS = {
	"LOADING_PAPER": _("Loading Paper"),
	"ABER_TOLL": _("Aber Toll"),
	"SHARJAH_TOLL": _("Sharjah Toll"),
	"FNRC_RECEIPT": _("FNRC Receipt"),
	"OFFLOADING_PAPER": _("Offloading Paper"),
}

VERIFICATION_STATUSES = ("PENDING_REVIEW", "APPROVED", "REJECTED")
REVIEWED_STATUSES = ("APPROVED", "REJECTED")

# extracted field -> (trip field, applies when)
# `None` as trip field means the value is informational only and is never written.
EXTRACTION_CANDIDATES = {
	"extracted_ticket_number": ("gdn", lambda document: True),
	"extracted_receipt_number": (None, lambda document: True),
	"extracted_document_datetime": (
		"pod_received_at",
		lambda document: document.document_type in ("LOADING_PAPER", "OFFLOADING_PAPER"),
	),
	"extracted_gross_weight": (None, lambda document: True),
	"extracted_tare_weight": (None, lambda document: True),
	"extracted_net_weight": (None, lambda document: True),
	"extracted_amount": (
		"__charge_amount__",
		lambda document: document.document_type in ("ABER_TOLL", "SHARJAH_TOLL", "FNRC_RECEIPT"),
	),
	"extracted_truck_number": (None, lambda document: True),
	"extracted_customer": (None, lambda document: True),
	"extracted_material": (None, lambda document: True),
	"extracted_destination": (None, lambda document: True),
	"extracted_station_or_gate": (None, lambda document: True),
}

CHARGE_FIELD_BY_DOCUMENT_TYPE = {
	"ABER_TOLL": "rak_toll",
	"SHARJAH_TOLL": "sharjah_toll",
	"FNRC_RECEIPT": "fnrc_extra_charge",
}

INFORMATIONAL_FIELDS = tuple(
	extracted_field
	for extracted_field, (trip_field, _) in EXTRACTION_CANDIDATES.items()
	if trip_field is None
)


def get_review_queue(filters=None, start=0, page_length=25) -> dict:
	"""Paginated list of trip documents awaiting dispatcher verification."""
	require_verification_access()

	start = max(int(start or 0), 0)
	page_length = min(int(page_length or 25), 200)

	query_filters = {"verification_status": ["in", ["PENDING_REVIEW"]]}
	filters = frappe._dict(filters or {})
	if filters.document_type:
		query_filters["document_type"] = filters.document_type
	if filters.transport_trip:
		query_filters["transport_trip"] = filters.transport_trip

	documents = frappe.get_all(
		"Transport Trip Document",
		filters=query_filters,
		fields=[
			"name",
			"transport_trip",
			"document_type",
			"upload_source",
			"uploaded_at",
			"ai_status",
			"ai_confidence",
			"verification_status",
			"uploaded_by_driver",
			"uploaded_by_employee",
		],
		order_by="uploaded_at desc",
		limit_start=start,
		limit_page_length=page_length,
	)
	total = frappe.db.count("Transport Trip Document", query_filters)

	return {
		"total": total,
		"start": start,
		"page_length": page_length,
		"documents": [serialize_document_row(row) for row in documents],
	}


def get_review_summary() -> dict:
	"""Backlog counters shown on the console dashboard."""
	require_verification_access()
	pending = frappe.db.count(
		"Transport Trip Document", {"verification_status": "PENDING_REVIEW"}
	)
	approved = frappe.db.count(
		"Transport Trip Document", {"verification_status": "APPROVED"}
	)
	rejected = frappe.db.count(
		"Transport Trip Document", {"verification_status": "REJECTED"}
	)
	by_type = frappe.get_all(
		"Transport Trip Document",
		filters={"verification_status": "PENDING_REVIEW"},
		fields=["document_type", {"COUNT": "name", "as": "count"}],
		group_by="document_type",
	)
	return {
		"pending_review": pending,
		"approved": approved,
		"rejected": rejected,
		"by_document_type": {
			row.document_type: int(row.count or 0) for row in by_type
		},
	}


def get_document_review(document_name) -> dict:
	"""Return one document with its extraction payload and trip context."""
	require_verification_access()
	document = get_document(document_name)
	return {
		"document": serialize_document(document),
		"candidates": get_extraction_candidates(document),
		"trip": build_trip_context(document.transport_trip),
		"permissions": {
			"can_apply": bool(
				is_verifier() and frappe.has_permission("Transport Trip", ptype="write")
			),
			"can_edit_document": frappe.has_permission(
				"Transport Trip Document", ptype="write"
			),
		},
	}


def apply_extraction(document_name, accepted_fields=None) -> dict:
	"""Write the explicitly accepted extraction values onto the Transport Trip.

	Only fields produced by :func:`get_extraction_candidates` are honoured and
	every one of them is a documentation/receipt field.  The trip status,
	quantities, rates, vehicle, driver, material and locations are out of scope.
	"""
	require_verification_access()
	document = get_document(document_name)
	candidates = get_extraction_candidates(document)
	writable = {row["extracted_field"] for row in candidates if row["can_write_trip"]}

	requested = frappe.parse_json(accepted_fields) if accepted_fields else []
	if not isinstance(requested, list):
		requested = [requested]

	accepted = []
	for entry in requested:
		fieldname = (entry or {}).get("extracted_field") if isinstance(entry, dict) else entry
		if fieldname in writable and fieldname not in accepted:
			accepted.append(fieldname)

	if not accepted:
		frappe.throw(_("Select at least one verified value to apply to the Transport Trip."))

	if document.verification_status == "APPROVED":
		frappe.throw(
			_("Transport Trip Document {0} has already been verified.").format(document.name)
		)

	# Approving an extraction writes authoritative trip data, so the verifier must
	# hold write permission on Transport Trip itself - not only the console role.
	if not frappe.has_permission("Transport Trip", ptype="write"):
		frappe.throw(
			_("You do not have permission to write Transport Trip, so verified values cannot be applied."),
			exc=FrappePermissionError,
		)

	trip = frappe.get_doc("Transport Trip", document.transport_trip)
	updates = {}
	for fieldname in accepted:
		candidate = next(row for row in candidates if row["extracted_field"] == fieldname)
		updates[candidate["trip_field"]] = candidate["extracted_value"]

	if updates:
		trip.update(updates)
		trip.save()

	document.verification_status = "APPROVED"
	document.verified_by = frappe.session.user
	document.verified_at = now_datetime()
	document.review_notes = build_review_notes("approved", accepted, candidates)
	document.save(ignore_permissions=True)

	trip.add_comment(
		"Info",
		_("Document {0} verified. Applied: {1}").format(
			document.name, ", ".join(accepted) or "none"
		),
	)

	return {
		"ok": True,
		"document": serialize_document(document),
		"applied_fields": accepted,
		"trip_updates": updates,
	}


def reject_document(document_name, review_notes=None) -> dict:
	"""Mark a document as rejected.  Rejection never writes trip data."""
	require_verification_access()
	document = get_document(document_name)

	document.verification_status = "REJECTED"
	document.verified_by = frappe.session.user
	document.verified_at = now_datetime()
	document.review_notes = (review_notes or "").strip() or _(
		"Rejected by the dispatcher without applying extracted values."
	)
	document.save(ignore_permissions=True)

	if frappe.db.exists("Transport Trip", document.transport_trip):
		frappe.get_doc("Transport Trip", document.transport_trip).add_comment(
			"Info", _("Document {0} rejected.").format(document.name)
		)

	return {"ok": True, "document": serialize_document(document)}


def reset_document(document_name) -> dict:
	"""Return a document to the pending review queue."""
	require_verification_access()
	document = get_document(document_name)
	document.verification_status = "PENDING_REVIEW"
	document.verified_by = None
	document.verified_at = None
	document.review_notes = None
	document.save(ignore_permissions=True)
	return {"ok": True, "document": serialize_document(document)}


def get_extraction_candidates(document) -> list[dict]:
	"""Allow-listed view of what an approved extraction would write."""
	trip = (
		frappe.db.get_value(
			"Transport Trip",
			document.transport_trip,
			["gdn", "pod_received_at", "rak_toll", "sharjah_toll", "fnrc_extra_charge"],
			as_dict=True,
		)
		if frappe.db.exists("Transport Trip", document.transport_trip)
		else frappe._dict()
	)

	candidates = []
	for extracted_field, (trip_field, applies) in EXTRACTION_CANDIDATES.items():
		value = document.get(extracted_field)
		if value is None:
			continue
		if not applies(document):
			continue

		if trip_field == "__charge_amount__":
			trip_field = CHARGE_FIELD_BY_DOCUMENT_TYPE.get(document.document_type)
			if not trip_field:
				continue

		current_value = trip.get(trip_field) if trip_field else None
		candidates.append(
			{
				"extracted_field": extracted_field,
				"label": _(extracted_field.replace("extracted_", "").replace("_", " ").title()),
				"extracted_value": value,
				"trip_field": trip_field,
				"current_value": current_value,
				"can_write_trip": bool(trip_field),
				"differs": bool(trip_field) and normalize(value) != normalize(current_value),
			}
		)
	return candidates


def build_review_notes(action, applied, candidates) -> str:
	labels = {
		row["extracted_field"]: str(row["label"])
		for row in candidates
		if row["extracted_field"] in applied
	}
	names = ", ".join(labels.get(field, field) for field in applied)
	prefix = _("Applied") if action == "approved" else _("Rejected")
	return "{0}: {1} ({2})".format(prefix, names or "none", now_datetime())


def get_document(document_name):
	if not document_name:
		frappe.throw(_("Transport Trip Document is required."))
	if not frappe.db.exists("Transport Trip Document", document_name):
		frappe.throw(
			_("Transport Trip Document {0} does not exist.").format(document_name),
			exc=frappe.DoesNotExistError,
		)
	return frappe.get_doc("Transport Trip Document", document_name)


def serialize_document(document) -> dict:
	return {
		"name": document.name,
		"transport_trip": document.transport_trip,
		"document_type": document.document_type,
		"document_type_label": DOCUMENT_TYPE_LABELS.get(
			document.document_type, document.document_type
		),
		"file": document.file,
		"upload_source": document.upload_source,
		"uploaded_at": str(document.uploaded_at or ""),
		"uploaded_by_driver": document.uploaded_by_driver,
		"uploaded_by_employee": document.uploaded_by_employee,
		"ai_status": document.ai_status,
		"ai_confidence": document.ai_confidence,
		"verification_status": document.verification_status,
		"verified_by": document.verified_by,
		"verified_at": str(document.verified_at or ""),
		"review_notes": document.review_notes,
		"extracted": {
			field: document.get(field)
			for field in EXTRACTION_CANDIDATES
			if field in INFORMATIONAL_FIELDS
		},
		"extracted_payload": parse_extracted_json(document.ai_extracted_json),
	}


def parse_extracted_json(payload):
	if not payload:
		return None
	try:
		parsed = frappe.parse_json(payload)
	except Exception:
		return None
	return parsed if isinstance(parsed, (dict, list)) else None


def serialize_document_row(row) -> dict:
	return {
		"name": row.name,
		"transport_trip": row.transport_trip,
		"document_type": row.document_type,
		"document_type_label": DOCUMENT_TYPE_LABELS.get(
			row.document_type, row.document_type
		),
		"upload_source": row.upload_source,
		"uploaded_at": str(row.uploaded_at or ""),
		"ai_status": row.ai_status,
		"ai_confidence": row.ai_confidence,
		"verification_status": row.verification_status,
		"uploaded_by_driver": row.uploaded_by_driver,
		"uploaded_by_employee": row.uploaded_by_employee,
	}


def build_trip_context(trip_name) -> dict | None:
	if not trip_name or not frappe.db.exists("Transport Trip", trip_name):
		return None
	from dispatch_portal.services.trip_console import get_trip_doc

	trip = get_trip_doc(trip_name)
	return {
		"trip": trip.name,
		"status": trip.status,
		"transport_job": trip.transport_job,
		"customer": frappe.db.get_value("Transport Job", trip.transport_job, "customer")
		if trip.transport_job
		else None,
		"loading_site": trip.loading_site,
		"unloading_site": trip.unloading_site,
		"trip_date": str(trip.trip_date or ""),
		"vehicle": trip.vehicle or trip.hired_vehicle,
		"driver": trip.driver or trip.hired_driver,
	}


def normalize(value) -> str:
	if value is None:
		return ""
	return str(value)
