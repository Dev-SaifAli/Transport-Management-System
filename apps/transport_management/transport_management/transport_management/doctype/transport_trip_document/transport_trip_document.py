# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime


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
		self.validate_loading_verification()
		self.validate_delivery_verification()
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

	def validate_loading_verification(self):
		if self.document_type != "LOADING_PAPER":
			return

		verified_fields = (
			"verified_material",
			"verified_loading_location",
			"verified_loading_date",
			"verified_loaded_quantity",
		)
		if not self.is_new():
			previous = frappe.db.get_value(
				self.doctype,
				self.name,
				[
					"verification_status",
					"verified_material",
					"verified_loading_location",
					"verified_loading_date",
					"verified_loaded_quantity",
					"verified_by",
					"verified_at",
					"review_notes",
				],
				as_dict=True,
			)
			if previous.verification_status in {"APPROVED", "REJECTED"} and any(
				self.get(fieldname) != previous.get(fieldname)
				for fieldname in (
					"verification_status",
					"verified_material",
					"verified_loading_location",
					"verified_loading_date",
					"verified_loaded_quantity",
					"verified_by",
					"verified_at",
					"review_notes",
				)
			):
				frappe.throw(_("Reviewed Loading Paper facts and audit details are immutable; create a controlled correction record."))
			if (
				self.verification_status != previous.verification_status
				and not self.flags.get("loading_document_review")
			):
				frappe.throw(_("Loading Paper verification must use the authorized review operation."))
		elif self.verification_status != "PENDING_REVIEW":
			frappe.throw(_("New Loading Papers must remain pending until reviewed by Operations."))

		if self.verification_status == "PENDING_REVIEW" and any(
			self.get(fieldname) for fieldname in (*verified_fields, "verified_by", "verified_at")
		):
			frappe.throw(_("Pending Loading Papers cannot contain verified facts or reviewer audit details."))

		if self.verification_status == "APPROVED":
			if not all((*(self.get(fieldname) for fieldname in verified_fields), self.verified_by, self.verified_at)):
				frappe.throw(_("Approved Loading Papers require verified facts and reviewer audit details."))
			quantity = flt(self.verified_loaded_quantity, 6)
			if quantity <= 0:
				frappe.throw(_("Verified Loaded Quantity must be greater than zero."))
			if getdate(self.verified_loading_date) > getdate():
				frappe.throw(_("Verified Loading Date cannot be in the future."))
		elif self.verification_status == "REJECTED":
			if not self.review_notes:
				frappe.throw(_("A review reason is required when rejecting a Loading Paper."))
			if not self.verified_by or not self.verified_at:
				frappe.throw(_("Rejected Loading Papers require reviewer audit details."))

	def validate_delivery_verification(self):
		if self.document_type != "OFFLOADING_PAPER":
			return

		verified_fields = ("verified_delivery_date", "verified_delivered_quantity")
		audit_fields = (*verified_fields, "verification_status", "verified_by", "verified_at", "review_notes")
		if not self.is_new():
			previous = frappe.db.get_value(
				self.doctype,
				self.name,
				audit_fields,
				as_dict=True,
			)
			if previous.verification_status in {"APPROVED", "REJECTED"} and any(
				self.get(fieldname) != previous.get(fieldname) for fieldname in audit_fields
			):
				frappe.throw(_("Reviewed Offloading Paper facts and audit details are immutable; create a controlled correction record."))
			if (
				self.verification_status != previous.verification_status
				and not self.flags.get("delivery_document_review")
			):
				frappe.throw(_("Offloading Paper verification must use the authorized review operation."))
		elif self.verification_status != "PENDING_REVIEW":
			frappe.throw(_("New Offloading Papers must remain pending until reviewed by Operations."))

		if self.verification_status == "PENDING_REVIEW" and any(
			self.get(fieldname) for fieldname in (*verified_fields, "verified_by", "verified_at")
		):
			frappe.throw(_("Pending Offloading Papers cannot contain verified facts or reviewer audit details."))

		if self.verification_status == "APPROVED":
			if not all(
				(*[self.get(fieldname) for fieldname in verified_fields], self.verified_by, self.verified_at)
			):
				frappe.throw(_("Approved Offloading Papers require verified delivery facts and reviewer audit details."))
			quantity = flt(self.verified_delivered_quantity, 6)
			if quantity <= 0:
				frappe.throw(_("Verified Delivered Quantity must be greater than zero."))
			if getdate(self.verified_delivery_date) > getdate():
				frappe.throw(_("Verified Delivery Date cannot be in the future."))
			loaded_quantity = flt(
				frappe.db.get_value("Transport Trip", self.transport_trip, "loaded_quantity"),
				6,
			)
			if loaded_quantity and quantity > loaded_quantity:
				frappe.throw(_("Verified Delivered Quantity cannot exceed Loaded Quantity."))
		elif self.verification_status == "REJECTED":
			if not self.review_notes:
				frappe.throw(_("A review reason is required when rejecting an Offloading Paper."))
			if not self.verified_by or not self.verified_at:
				frappe.throw(_("Rejected Offloading Papers require reviewer audit details."))

	def validate_single_document_type_duplicate(self):
		if self.document_type not in SINGLE_DOCUMENT_TYPES or not self.transport_trip:
			return

		existing = frappe.db.exists(
			"Transport Trip Document",
			{
				"transport_trip": self.transport_trip,
				"document_type": self.document_type,
				"verification_status": ["!=", "REJECTED"],
				"name": ["!=", self.name or ""],
			},
		)
		if existing:
			frappe.throw(
				_("{0} has already been uploaded for this Transport Trip.").format(self.document_type),
				frappe.DuplicateEntryError,
			)
