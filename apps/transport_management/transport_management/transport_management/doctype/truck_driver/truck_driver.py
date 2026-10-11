# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TruckDriver(Document):
	def before_save(self):
		if self.status != "Active":
			clear_default_driver_from_trucks(self.name)


def clear_default_driver_from_trucks(driver):
	for truck in frappe.get_all("Truck", filters={"trans_ms_driver": driver}, pluck="name"):
		frappe.db.set_value(
			"Truck",
			truck,
			{
				"trans_ms_driver": "",
				"trans_ms__driver_name": "",
			},
		)
