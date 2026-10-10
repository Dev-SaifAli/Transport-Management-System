"""Dispatcher verification API.

Every call requires verification authorisation server-side.  Approvals only
write allow-listed documentation fields onto the trip - trip status, quantities
and commercial values can never be overwritten by an AI extraction.
"""

from __future__ import annotations

import frappe

from dispatch_portal.services.verification_service import (
	apply_extraction,
	get_document_review,
	get_review_queue,
	get_review_summary,
	reject_document,
	reset_document,
)


@frappe.whitelist()
def get_verification_queue(filters=None, start=0, page_length=25):
	return get_review_queue(filters=filters, start=start, page_length=page_length)


@frappe.whitelist()
def get_verification_summary():
	return get_review_summary()


@frappe.whitelist()
def get_verification_document(document_name):
	return get_document_review(document_name)


@frappe.whitelist(methods=["POST"])
def apply_extraction_values(document_name, accepted_fields=None):
	return apply_extraction(document_name, accepted_fields)


@frappe.whitelist(methods=["POST"])
def reject_document_review(document_name, review_notes=None):
	return reject_document(document_name, review_notes)


@frappe.whitelist(methods=["POST"])
def reset_document_review(document_name):
	return reset_document(document_name)


@frappe.whitelist()
def get_document_types():
	from dispatch_portal.services.verification_service import DOCUMENT_TYPE_LABELS

	return [
		{"value": key, "label": str(label)}
		for key, label in DOCUMENT_TYPE_LABELS.items()
	]
