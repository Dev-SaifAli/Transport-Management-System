# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CargoTypes(Document):
	def validate(self):
		self.validate_allowed_truck_types()

	def validate_allowed_truck_types(self):
		seen = set()
		for row in self.get("allowed_truck_types", []):
			if not row.truck_type:
				continue
			if row.truck_type in seen:
				frappe.throw(f"Duplicate allowed Truck Type: {row.truck_type}")
			seen.add(row.truck_type)
