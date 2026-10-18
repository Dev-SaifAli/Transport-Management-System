"""Tag existing Transport Sales Orders with the legacy fixed-quantity mode."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.has_column("Transport Sales Order", "order_mode"):
		return

	for order in frappe.get_all(
		"Transport Sales Order",
		fields=["name", "order_mode"],
		limit_page_length=0,
	):
		if not order.order_mode:
			frappe.db.set_value(
				"Transport Sales Order",
				order.name,
				"order_mode",
				"Fixed Quantity",
				update_modified=False,
			)
