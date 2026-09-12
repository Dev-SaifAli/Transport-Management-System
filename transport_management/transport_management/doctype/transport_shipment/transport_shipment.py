# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class TransportShipment(Document):
	def validate(self):
		quantity = flt(self.quantity)
		if not isfinite(quantity) or quantity <= 0:
			frappe.throw(_("Shipment quantity must be greater than zero."))

		if self.loading_site and self.loading_site == self.offloading_site:
			frappe.throw(_("Loading Site and Offloading Site must be different."))

		if not self.transport_order:
			frappe.throw(_("Transportation Order is required."))
		customer = frappe.db.get_value("Transportation Order", self.transport_order, "customer")
		if not customer:
			frappe.throw(_("Select a Transportation Order with a Customer before saving the shipment."))
		if self.customer and self.customer != customer:
			frappe.throw(_("Shipment Customer must match the Transportation Order Customer."))
		self.customer = customer
