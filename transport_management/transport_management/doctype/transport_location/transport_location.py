# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class TransportLocation(Document):
	def before_validate(self):
		if self.active is None:
			self.active = 1
