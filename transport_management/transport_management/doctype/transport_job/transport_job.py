# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from transport_management.location_master import validate_active_transport_locations


class TransportJob(Document):
	def validate(self):
		quantity = flt(self.requested_quantity)
		if not isfinite(quantity) or quantity <= 0:
			frappe.throw(_("Requested Quantity must be greater than zero."))

		if self.loading_site and self.loading_site == self.unloading_site:
			frappe.throw(_("Loading Site and Unloading Site must be different."))

		validate_active_transport_locations(
			self,
			(("loading_site", _("Loading Site")), ("unloading_site", _("Unloading Site"))),
		)
