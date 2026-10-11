"""Cleanup helpers for retiring the old Fleet compatibility surface."""

import frappe


def retire_transport_shipment_and_cleanup_fleet_customizations():
	"""Remove stale TMS customizations from legacy Fleet metadata.

	Transport Shipment metadata is synced from its DocType JSON. This helper only
	cleans database customization rows that transport_management previously added
	to Transportation Order during early compatibility work.
	"""

	frappe.db.delete("Custom Field", {"dt": "Transportation Order", "module": "Transport Management"})
	frappe.db.delete("Property Setter", {"doc_type": "Transportation Order", "module": "Transport Management"})
	remove_orphaned_fleet_navigation()
	frappe.clear_cache(doctype="Transportation Order")
	frappe.clear_cache(doctype="Transport Shipment")


def remove_orphaned_fleet_navigation():
	"""Remove legacy Fleet navigation records left behind after uninstall."""

	for doctype, name in (("Desktop Icon", "Fleet MS"), ("Workspace Sidebar", "Fleet MS")):
		if frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
