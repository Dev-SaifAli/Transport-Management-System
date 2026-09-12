# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class HiredVehicle(Document):
	def before_validate(self):
		if self.active is None:
			self.active = 1
		if self.plate_number:
			self.plate_number = self.plate_number.strip()

	def validate(self):
		validate_transporter_supplier(self.transporter)
		if not self.plate_number:
			frappe.throw(_("Plate Number is required."))
		self.validate_duplicate_plate()

	def validate_duplicate_plate(self):
		existing = frappe.db.get_value(
			"Hired Vehicle",
			{
				"transporter": self.transporter,
				"plate_number": self.plate_number,
				"name": ["!=", self.name],
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("Hired Vehicle plate {0} already exists for Transporter {1}.").format(
					frappe.bold(self.plate_number), frappe.bold(self.transporter)
				)
			)


def validate_transporter_supplier(transporter):
	if not transporter:
		frappe.throw(_("Transporter is required."))

	supplier = frappe.db.get_value(
		"Supplier",
		transporter,
		["is_transporter", "disabled"],
		as_dict=True,
	)
	if not supplier:
		frappe.throw(_("Transporter Supplier must exist."))
	if not cint(supplier.is_transporter):
		frappe.throw(_("Selected Supplier must be marked as a Transporter."))
	if cint(supplier.disabled):
		frappe.throw(_("Disabled Suppliers cannot be used as Transporters."))
