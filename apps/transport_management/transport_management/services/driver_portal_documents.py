"""Driver Portal trip document upload and document-summary helpers."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import format_datetime, now_datetime
from frappe.utils.file_manager import save_file

from transport_management.services.driver_portal_auth import require_current_driver_identity

ALLOWED_DOCUMENT_TYPES = {
	"LOADING_PAPER",
	"ABER_TOLL",
	"SHARJAH_TOLL",
	"FNRC_RECEIPT",
	"OFFLOADING_PAPER",
}
SINGLE_DOCUMENT_TYPES = {"LOADING_PAPER", "OFFLOADING_PAPER"}
MULTIPLE_DOCUMENT_TYPES = {"ABER_TOLL", "SHARJAH_TOLL", "FNRC_RECEIPT"}
ALLOWED_UPLOAD_STATUSES = {"ASSIGNED", "IN_TRANSIT", "DELIVERED"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
DRIVER_SAFE_FIELDS = [
	"name",
	"transport_trip",
	"document_type",
	"uploaded_at",
	"upload_source",
	"ai_status",
	"verification_status",
]


@dataclass
class UploadedFileContent:
	filename: str
	content: bytes
	content_type: str | None = None


def upload_trip_document(trip_id=None, document_type=None, file=None, **kwargs) -> dict:
	identity = require_current_driver_identity()
	trip = get_owned_trip(trip_id, identity.truck_driver)
	validate_upload_status(trip.status)
	document_type = normalize_document_type(document_type)
	validate_duplicate_rule(trip.name, document_type)
	uploaded_file = get_uploaded_file_content(file)
	validate_uploaded_file(uploaded_file)

	file_doc = save_file(
		uploaded_file.filename,
		uploaded_file.content,
		"Transport Trip",
		trip.name,
		is_private=1,
	)
	document = frappe.get_doc(
		{
			"doctype": "Transport Trip Document",
			"transport_trip": trip.name,
			"document_type": document_type,
			"file": file_doc.file_url,
			"uploaded_by_driver": identity.truck_driver,
			"uploaded_by_employee": identity.employee,
			"uploaded_at": now_datetime(),
			"upload_source": "DRIVER_PORTAL",
			"ai_status": "NOT_PROCESSED",
			"verification_status": "PENDING_REVIEW",
		}
	).insert(ignore_permissions=True)
	attach_file_to_trip_document(file_doc.name, document.name)
	add_trip_document_uploaded_audit(document, identity)
	return {
		"ok": True,
		"document": serialize_document_for_driver(document),
	}


def get_trip_documents(trip_id=None, **kwargs) -> dict:
	identity = require_current_driver_identity()
	trip = get_owned_trip(trip_id, identity.truck_driver)
	return {
		"ok": True,
		"trip_id": trip.name,
		"documents": [
			serialize_document_for_driver(row)
			for row in get_trip_document_rows(trip.name)
		],
	}


def get_owned_trip(trip_id, driver: str) -> frappe._dict:
	trip_id = (str(trip_id or "").strip())
	if not trip_id:
		raise_trip_not_found()
	trip = frappe.db.get_value(
		"Transport Trip",
		trip_id,
		["name", "driver", "status"],
		as_dict=True,
	)
	if not trip or trip.driver != driver:
		raise_trip_not_found()
	return trip


def normalize_document_type(document_type) -> str:
	document_type = str(document_type or "").strip().upper()
	if document_type not in ALLOWED_DOCUMENT_TYPES:
		frappe.local.response["http_status_code"] = 417
		frappe.throw(_("Invalid document type."), frappe.ValidationError)
	return document_type


def validate_upload_status(status: str | None) -> None:
	if status in ALLOWED_UPLOAD_STATUSES:
		return
	frappe.local.response["http_status_code"] = 417
	frappe.throw(_("Documents cannot be uploaded for trip status {0}.").format(status or "-"), frappe.ValidationError)


def validate_duplicate_rule(trip_id: str, document_type: str) -> None:
	if document_type not in SINGLE_DOCUMENT_TYPES:
		return
	if frappe.db.exists(
		"Transport Trip Document",
		{
			"transport_trip": trip_id,
			"document_type": document_type,
		},
	):
		frappe.local.response["http_status_code"] = 409
		frappe.throw(
			_("{0} has already been uploaded for this Transport Trip.").format(document_type),
			frappe.DuplicateEntryError,
		)


def get_uploaded_file_content(file=None) -> UploadedFileContent:
	if file is None:
		request = getattr(frappe.local, "request", None)
		if request and getattr(request, "files", None):
			file = request.files.get("file")

	if file is None:
		frappe.local.response["http_status_code"] = 417
		frappe.throw(_("File is required."), frappe.ValidationError)

	filename = getattr(file, "filename", None) or getattr(file, "name", None)
	content_type = getattr(file, "content_type", None) or getattr(file, "mimetype", None)
	if hasattr(file, "read"):
		content = file.read()
	else:
		content = file

	if isinstance(content, str):
		frappe.local.response["http_status_code"] = 417
		frappe.throw(_("Unsupported file payload."), frappe.ValidationError)
	if not filename or not content:
		frappe.local.response["http_status_code"] = 417
		frappe.throw(_("A non-empty file is required."), frappe.ValidationError)

	return UploadedFileContent(filename=str(filename), content=content, content_type=content_type)


def validate_uploaded_file(uploaded_file: UploadedFileContent) -> None:
	if len(uploaded_file.content) > MAX_UPLOAD_SIZE:
		frappe.local.response["http_status_code"] = 413
		frappe.throw(_("File size exceeds the 10 MB limit."), frappe.ValidationError)

	guessed_content_type = mimetypes.guess_type(uploaded_file.filename)[0]
	content_type = uploaded_file.content_type or guessed_content_type
	if content_type not in ALLOWED_MIME_TYPES:
		frappe.local.response["http_status_code"] = 417
		frappe.throw(_("Unsupported file type."), frappe.ValidationError)
	if guessed_content_type and uploaded_file.content_type and guessed_content_type != uploaded_file.content_type:
		frappe.local.response["http_status_code"] = 417
		frappe.throw(_("File extension does not match the uploaded file type."), frappe.ValidationError)


def attach_file_to_trip_document(file_name: str, document_name: str) -> None:
	frappe.db.set_value(
		"File",
		file_name,
		{
			"attached_to_doctype": "Transport Trip Document",
			"attached_to_name": document_name,
			"attached_to_field": "file",
		},
		update_modified=False,
	)


def get_trip_document_rows(trip_id: str) -> list[frappe._dict]:
	return frappe.get_all(
		"Transport Trip Document",
		filters={"transport_trip": trip_id},
		fields=DRIVER_SAFE_FIELDS,
		order_by="creation asc",
		limit_page_length=0,
	)


def get_trip_document_summary(trip, required_documents: list[str]) -> dict:
	rows = get_trip_document_rows(trip.name)
	uploaded_types = {row.document_type for row in rows}
	required_types = set(required_documents or [])
	required_uploaded_types = uploaded_types & required_types

	if not rows:
		document_status = "MISSING"
	elif required_types and required_types <= uploaded_types:
		document_status = "COMPLETE"
	elif required_uploaded_types or uploaded_types:
		document_status = "PARTIAL"
	else:
		document_status = "MISSING"

	return {
		"document_status": document_status,
		"loading_paper_status": get_type_status(rows, "LOADING_PAPER"),
		"offloading_paper_status": get_type_status(rows, "OFFLOADING_PAPER"),
		"toll_document_count": sum(1 for row in rows if row.document_type in MULTIPLE_DOCUMENT_TYPES),
		"documents_pending_review": sum(1 for row in rows if row.verification_status == "PENDING_REVIEW"),
		"ai_review_status": get_ai_review_status(rows),
	}


def get_type_status(rows: list[frappe._dict], document_type: str) -> str:
	type_rows = [row for row in rows if row.document_type == document_type]
	if not type_rows:
		return "MISSING"
	if any(row.verification_status == "REJECTED" for row in type_rows):
		return "REJECTED"
	if any(row.verification_status == "APPROVED" for row in type_rows):
		return "VERIFIED"
	return "UPLOADED"


def get_ai_review_status(rows: list[frappe._dict]) -> str:
	if not rows:
		return "NOT_PROCESSED"
	statuses = {row.ai_status for row in rows}
	if "FAILED" in statuses:
		return "FAILED"
	if "PROCESSING" in statuses:
		return "PROCESSING"
	if "PENDING" in statuses:
		return "PENDING"
	if statuses == {"PROCESSED"}:
		return "PROCESSED"
	return "NOT_PROCESSED"


def serialize_document_for_driver(document) -> dict:
	return {
		"document_id": document.name,
		"trip_id": document.transport_trip,
		"document_type": document.document_type,
		"uploaded_at": format_datetime(document.uploaded_at) if document.uploaded_at else None,
		"ai_status": document.ai_status,
		"verification_status": document.verification_status,
		"can_reupload": document.document_type not in SINGLE_DOCUMENT_TYPES,
	}


def add_trip_document_uploaded_audit(document, identity: frappe._dict) -> None:
	trip = frappe.get_doc("Transport Trip", document.transport_trip)
	trip.add_comment(
		"Info",
		(
			"DRIVER_TRIP_DOCUMENT_UPLOADED<br>"
			f"Source: DRIVER_PORTAL<br>"
			f"Document: {document.name}<br>"
			f"Document Type: {document.document_type}<br>"
			f"Driver: {identity.truck_driver}<br>"
			f"Employee: {identity.employee}<br>"
			f"Uploaded At: {format_datetime(document.uploaded_at)}"
		),
	)


def raise_trip_not_found() -> None:
	frappe.local.response["http_status_code"] = 404
	frappe.throw(_("Trip not found or not permitted."), frappe.PermissionError)


def process_trip_document(document_id: str) -> None:
	"""Reserved no-op extension point for future OCR/AI processing."""
	return None
