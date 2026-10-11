# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
	validate_location_usage,
	validate_ton_uom,
)


class TransportRate(Document):
	def before_validate(self):
		if not self.uom:
			self.uom = "TON"
		if self.active is None:
			self.active = 1

	def validate(self):
		validate_ton_uom(self.uom)
		validate_location_usage(self.loading_location, {"Loading", "Both"}, "Loading Location")
		validate_location_usage(self.unloading_location, {"Unloading", "Both"}, "Unloading Location")

