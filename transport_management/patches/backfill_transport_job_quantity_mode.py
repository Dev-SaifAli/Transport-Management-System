"""Tag existing Transport Jobs with the legacy fixed-quantity mode."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.has_column("Transport Job", "quantity_mode"):
		return

	for job in frappe.get_all(
		"Transport Job",
		fields=["name", "quantity_mode"],
		limit_page_length=0,
	):
		if not job.quantity_mode:
			frappe.db.set_value(
				"Transport Job",
				job.name,
				"quantity_mode",
				"Fixed Quantity",
				update_modified=False,
			)
