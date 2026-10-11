# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class TransportShipment(Document):
	def before_insert(self):
		frappe.throw(_("Transport Shipment is retired. Use Transport Job and Transport Trip instead."))

	def validate(self):
		quantity = flt(self.quantity)
		if not isfinite(quantity) or quantity <= 0:
			frappe.throw(_("Shipment quantity must be greater than zero."))

		if self.loading_site and self.loading_site == self.offloading_site:
			frappe.throw(_("Loading Site and Offloading Site must be different."))
