"""Truck Driver ownership helpers for transport_management."""

import frappe
from frappe import _
from frappe.modules import reload_doc

TRUCK_DRIVER = "Truck Driver"
TRUCK_DRIVER_MODULE = "Transport Management"


def migrate_truck_driver_ownership():
	"""Make Truck Driver a native transport_management DocType."""
	reload_doc("transport_management", "doctype", "truck_driver", force=True)
	frappe.clear_cache(doctype=TRUCK_DRIVER)

	validate_truck_driver_metadata()
	frappe.db.set_value("DocType", TRUCK_DRIVER, "module", TRUCK_DRIVER_MODULE, update_modified=False)
	frappe.clear_cache(doctype=TRUCK_DRIVER)
	return "Truck Driver ownership migrated"


def validate_truck_driver_metadata():
	meta = frappe.get_meta(TRUCK_DRIVER, cached=False)
	expected_fields = {
		"full_name": ("Data", None, True),
		"status": ("Select", "Active\nSuspended\nLeft", True),
		"cell_number": ("Data", None, True),
		"employee": ("Link", "Employee", False),
		"in_trip": ("Check", None, False),
	}
	for fieldname, (fieldtype, options, required) in expected_fields.items():
		field = meta.get_field(fieldname)
		if not field or field.fieldtype != fieldtype:
			frappe.throw(_("Truck Driver.{0} must exist as a {1} field.").format(fieldname, fieldtype))
		if options and field.options != options:
			frappe.throw(_("Truck Driver.{0} has unexpected options.").format(fieldname))
		if required and not field.reqd:
			frappe.throw(_("Truck Driver.{0} must remain required.").format(fieldname))

	if not meta.get_field("cell_number").unique:
		frappe.throw(_("Truck Driver.cell_number must remain unique."))
