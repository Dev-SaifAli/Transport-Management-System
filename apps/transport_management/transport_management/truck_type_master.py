"""Truck Type ownership helpers for transport_management."""

import frappe
from frappe import _
from frappe.modules import reload_doc
from frappe.model.rename_doc import rename_doc

TRUCK_TYPE = "Truck Type"
TRUCK_TYPE_MODULE = "Transport Management"
LEGACY_BULKER_TYPE = "BULKER"
CANONICAL_TANKER_TYPE = "TANKER"


def _update_vehicle_type_links(old_type, new_type):
	updated = 0
	for doctype in ("Truck", "Hired Vehicle"):
		if not frappe.db.table_exists(doctype):
			continue
		for name in frappe.get_all(doctype, filters={"vehicle_type": old_type}, pluck="name"):
			frappe.db.set_value(doctype, name, "vehicle_type", new_type, update_modified=False)
			updated += 1
	return updated


def migrate_truck_type_ownership():
	"""Make Truck Type a native transport_management DocType.

	Reloading from transport_management after app sync keeps the live DocType
	ownership stable.
	"""
	reload_doc("transport_management", "doctype", "truck_type", force=True)
	frappe.clear_cache(doctype=TRUCK_TYPE)

	field = frappe.get_meta(TRUCK_TYPE, cached=False).get_field("truck_type")
	if not field or field.fieldtype != "Data":
		frappe.throw(_("Truck Type.truck_type must exist as a Data field."))
	if not field.unique:
		frappe.throw(_("Truck Type.truck_type must remain unique."))

	frappe.db.set_value("DocType", TRUCK_TYPE, "module", TRUCK_TYPE_MODULE, update_modified=False)
	frappe.clear_cache(doctype=TRUCK_TYPE)
	return "Truck Type ownership migrated"


def normalize_operational_truck_types():
	"""Replace legacy BULKER terminology with canonical TANKER.

	The old source PDF was named "Bulker", but the TMS business master now uses
	TANKER. If no legacy/current records exist, this helper stays hands-off so
	the owned truck importer can create TANKER later during an approved import.
	"""
	bulker_exists = frappe.db.exists(TRUCK_TYPE, LEGACY_BULKER_TYPE)
	tanker_exists = frappe.db.exists(TRUCK_TYPE, CANONICAL_TANKER_TYPE)

	if bulker_exists and not tanker_exists:
		rename_doc(
			doctype=TRUCK_TYPE,
			old=LEGACY_BULKER_TYPE,
			new=CANONICAL_TANKER_TYPE,
			force=True,
			ignore_permissions=True,
			show_alert=False,
		)
	elif tanker_exists:
		_update_vehicle_type_links(LEGACY_BULKER_TYPE, CANONICAL_TANKER_TYPE)
		if bulker_exists and not _count_vehicle_type_links(LEGACY_BULKER_TYPE):
			frappe.delete_doc(TRUCK_TYPE, LEGACY_BULKER_TYPE, force=True, ignore_permissions=True)

	frappe.clear_cache(doctype=TRUCK_TYPE)
	return {
		"bulker_exists": bool(frappe.db.exists(TRUCK_TYPE, LEGACY_BULKER_TYPE)),
		"tanker_exists": bool(frappe.db.exists(TRUCK_TYPE, CANONICAL_TANKER_TYPE)),
		"bulker_links": _count_vehicle_type_links(LEGACY_BULKER_TYPE),
		"tanker_links": _count_vehicle_type_links(CANONICAL_TANKER_TYPE),
	}


def _count_vehicle_type_links(vehicle_type):
	count = 0
	for doctype in ("Truck", "Hired Vehicle"):
		if frappe.db.table_exists(doctype):
			count += frappe.db.count(doctype, {"vehicle_type": vehicle_type})
	return count
