# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


DOCUMENT_TYPES = {
	"LOADING_PAPER",
	"ABER_TOLL",
	"SHARJAH_TOLL",
	"FNRC_RECEIPT",
	"OFFLOADING_PAPER",
}
SINGLE_DOCUMENT_TYPES = {"LOADING_PAPER", "OFFLOADING_PAPER"}
AI_STATUSES = {"NOT_PROCESSED", "PENDING", "PROCESSING", "PROCESSED", "FAILED"}
VERIFICATION_STATUSES = {"PENDING_REVIEW", "APPROVED", "REJECTED"}
UPLOAD_SOURCES = {"DRIVER_PORTAL", "BACK_OFFICE"}


class TransportTripDocument(Document):
	def before_validate(self):
		if not self.uploaded_at:
			self.uploaded_at = now_datetime()
		if not self.upload_source:
			self.upload_source = "DRIVER_PORTAL"
		if not self.ai_status:
			self.ai_status = "NOT_PROCESSED"
		if not self.verification_status:
			self.verification_status = "PENDING_REVIEW"

	def validate(self):
		self.validate_transport_trip()
		self.validate_document_type()
		self.validate_upload_source()
		self.validate_processing_statuses()
		self.validate_single_document_type_duplicate()

	def validate_transport_trip(self):
		if not self.transport_trip or not frappe.db.exists("Transport Trip", self.transport_trip):
			frappe.throw(_("Transport Trip must exist."))

	def validate_document_type(self):
		if self.document_type not in DOCUMENT_TYPES:
			frappe.throw(_("Invalid Transport Trip Document Type {0}.").format(self.document_type))

	def validate_upload_source(self):
		if self.upload_source not in UPLOAD_SOURCES:
			frappe.throw(_("Invalid Upload Source {0}.").format(self.upload_source))

	def validate_processing_statuses(self):
		if self.ai_status not in AI_STATUSES:
			frappe.throw(_("Invalid AI Status {0}.").format(self.ai_status))
		if self.verification_status not in VERIFICATION_STATUSES:
			frappe.throw(_("Invalid Verification Status {0}.").format(self.verification_status))

	def validate_single_document_type_duplicate(self):
		if self.document_type not in SINGLE_DOCUMENT_TYPES or not self.transport_trip:
			return

		existing = frappe.db.exists(
			"Transport Trip Document",
			{
				"transport_trip": self.transport_trip,
				"document_type": self.document_type,
				"name": ["!=", self.name or ""],
			},
		)
		if existing:
			frappe.throw(
				_("{0} has already been uploaded for this Transport Trip.").format(self.document_type),
				frappe.DuplicateEntryError,
			)
