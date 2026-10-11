"""Navigation sync and cleanup helpers for Transport Management."""

from __future__ import annotations

import json
from pathlib import Path

import frappe


OBSOLETE_WRAPPER_PAGES = (
	"tms-customers",
	"tms-suppliers",
	"tms-owned-trucks",
	"tms-drivers",
	"tms-locations",
)

OBSOLETE_DESKTOP_ICONS = ("Transport Management", "AL RANA TMS")
OBSOLETE_WORKSPACE_SIDEBARS = ("Transport Management", "AL RANA TMS")


def sync_tms_navigation():
	"""Remove obsolete wrapper pages and sync source-controlled TMS navigation."""
	remove_obsolete_wrapper_pages()
	sync_json_document("workspace_sidebar/tms.json")
	sync_json_document("desktop_icon/tms.json")
	remove_obsolete_desktop_icons()
	remove_obsolete_workspace_sidebars()
	sync_transport_management_dashboard_widgets()
	sync_json_document(
		"transport_management/workspace/transport_management/transport_management.json"
	)
	frappe.clear_cache()
	return "TMS navigation synced"


def sync_transport_management_dashboard_widgets():
	"""Sync native widgets used by the Transport Management workspace."""
	for relative_path in (
		"transport_management/number_card/active_jobs/active_jobs.json",
		"transport_management/number_card/trips_en_route/trips_en_route.json",
		"transport_management/number_card/available_fleet/available_fleet.json",
		"transport_management/number_card/pending_sales_orders/pending_sales_orders.json",
		"transport_management/dashboard_chart/monthly_fleet_utilization/monthly_fleet_utilization.json",
	):
		sync_json_document(relative_path)


def remove_obsolete_wrapper_pages():
	for page in OBSOLETE_WRAPPER_PAGES:
		frappe.delete_doc_if_exists("Page", page, force=True, ignore_permissions=True)


def remove_obsolete_desktop_icons():
	for icon in OBSOLETE_DESKTOP_ICONS:
		frappe.delete_doc_if_exists("Desktop Icon", icon, force=True, ignore_permissions=True)


def remove_obsolete_workspace_sidebars():
	for sidebar in OBSOLETE_WORKSPACE_SIDEBARS:
		frappe.delete_doc_if_exists("Workspace Sidebar", sidebar, force=True, ignore_permissions=True)


def sync_json_document(relative_path):
	path = Path(frappe.get_app_path("transport_management")) / relative_path
	data = json.loads(path.read_text())
	doc = get_or_create_document(data)

	for fieldname, value in data.items():
		if is_standard_field(fieldname) or isinstance(value, list):
			continue
		doc.set(fieldname, value)

	for fieldname, value in data.items():
		if not isinstance(value, list):
			continue
		doc.set(fieldname, [])
		for row in value:
			doc.append(fieldname, row)

	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)
	return data


def get_or_create_document(data):
	doctype = data["doctype"]
	name = data["name"]
	if frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)

	doc = frappe.new_doc(doctype)
	doc.name = name
	return doc


def is_standard_field(fieldname):
	return fieldname in {
		"creation",
		"docstatus",
		"doctype",
		"idx",
		"modified",
		"modified_by",
		"name",
		"owner",
	}
