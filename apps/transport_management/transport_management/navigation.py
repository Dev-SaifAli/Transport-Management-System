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

# Source-controlled sidebars for the AL RANA workspaces. Frappe only auto-generates
# a sidebar when a workspace is saved interactively, so these are synced from the
# JSON fixtures alongside the TMS sidebar.
AL_RANA_SIDEBAR_WORKSPACES = (
	"al_rana_operations",
	"al_rana_dispatcher",
	"al_rana_expenses",
	"al_rana_finance",
	"al_rana_hr",
	"al_rana_admin",
)

# Derived-configuration documents that may be recreated from the JSON source
# when a set-only-once field cannot be reconciled in place. Scoped to this one
# chart so the sync can never delete any other existing document.
RECONCILABLE_ON_SET_ONCE_CONFLICT = {("Dashboard Chart", "Monthly Fleet Utilization")}


def sync_tms_navigation():
	"""Remove obsolete wrapper pages and sync source-controlled TMS navigation."""
	remove_obsolete_wrapper_pages()
	sync_json_document("workspace_sidebar/tms.json")
	for workspace in AL_RANA_SIDEBAR_WORKSPACES:
		sync_json_document(f"workspace_sidebar/{workspace}.json")
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
		doc = frappe.get_doc(doctype, name)
		if (
			(doctype, name) in RECONCILABLE_ON_SET_ONCE_CONFLICT
			and _has_set_only_once_conflict(doc, data)
		):
			# The JSON is the source of truth and a set-only-once field cannot be
			# updated in place, so this known derived-configuration document is
			# recreated from source. The allow-list keeps the blast radius to this
			# single chart; no other synced document is ever deleted.
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
			doc = frappe.new_doc(doctype)
			doc.name = name
		return doc

	doc = frappe.new_doc(doctype)
	doc.name = name
	return doc


def _has_set_only_once_conflict(doc, data):
	"""Return True when a set-only-once field differs from the source JSON."""
	for df in frappe.get_meta(doc.doctype).get_set_only_once_fields():
		fieldname = df.fieldname
		if is_standard_field(fieldname):
			continue
		if (data.get(fieldname) or None) != (doc.get(fieldname) or None):
			return True
	return False


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
