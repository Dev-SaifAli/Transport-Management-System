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


def sync_tms_navigation():
	"""Remove obsolete wrapper pages and sync source-controlled TMS navigation."""
	remove_obsolete_wrapper_pages()
	sync_json_document("workspace_sidebar/transport_management.json")
	sync_json_document(
		"transport_management/workspace/transport_management/transport_management.json"
	)
	frappe.clear_cache()
	return "TMS navigation synced"


def remove_obsolete_wrapper_pages():
	for page in OBSOLETE_WRAPPER_PAGES:
		frappe.delete_doc_if_exists("Page", page, force=True, ignore_permissions=True)


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
