import frappe
from frappe.model.document import Document


class Truck(Document):
	def autoname(self):
		self.set_tms_defaults()
		if self.truck_number:
			self.name = self.truck_number

	def before_validate(self):
		self.set_tms_defaults()

	def before_save(self):
		self.set_tms_defaults()

	def set_tms_defaults(self):
		if not self.truck_number and self.license_plate:
			self.truck_number = self.license_plate

		if self.status == "Disabled":
			self.disabled = 1
		elif self.disabled:
			self.status = "Disabled"
