"""Transport Location customizations owned by transport_management."""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import cint

LOCATION = "Transport Location"
LOCATION_TYPE_OPTIONS = "Customer Site\nSupplier Site\nPlant\nYard\nWarehouse\nPort\nOther"

CUSTOM_LOCATION_FIELDS = (
	{
		"fieldname": "location_type",
		"label": "Location Type",
		"fieldtype": "Select",
		"options": LOCATION_TYPE_OPTIONS,
		"insert_after": "country",
		"module": "Transport Management",
		"description": "Operational site type owned by transport_management.",
	},
	{
		"fieldname": "customer",
		"label": "Customer",
		"fieldtype": "Link",
		"options": "Customer",
		"insert_after": "location_type",
		"module": "Transport Management",
	},
	{
		"fieldname": "supplier",
		"label": "Supplier",
		"fieldtype": "Link",
		"options": "Supplier",
		"insert_after": "customer",
		"module": "Transport Management",
	},
	{
		"fieldname": "address",
		"label": "Address",
		"fieldtype": "Link",
		"options": "Address",
		"insert_after": "supplier",
		"module": "Transport Management",
	},
	{
		"fieldname": "city",
		"label": "City",
		"fieldtype": "Data",
		"insert_after": "address",
		"module": "Transport Management",
	},
	{
		"fieldname": "latitude",
		"label": "Latitude",
		"fieldtype": "Float",
		"insert_after": "city",
		"module": "Transport Management",
	},
	{
		"fieldname": "longitude",
		"label": "Longitude",
		"fieldtype": "Float",
		"insert_after": "latitude",
		"module": "Transport Management",
	},
	{
		"fieldname": "active",
		"label": "Active",
		"fieldtype": "Check",
		"default": "1",
		"insert_after": "longitude",
		"module": "Transport Management",
	},
	{
		"fieldname": "notes",
		"label": "Notes",
		"fieldtype": "Small Text",
		"insert_after": "active",
		"module": "Transport Management",
	},
)


def ensure_transport_location_fields():
	"""Extend Fleet's Transport Location without editing Fleet source metadata."""
	meta = frappe.get_meta(LOCATION, cached=False)
	for fieldname, fieldtype in (("location", "Data"), ("country", "Link")):
		field = meta.get_field(fieldname)
		if not field or field.fieldtype != fieldtype:
			frappe.throw(_("Transport Location.{0} must exist as a {1} field.").format(fieldname, fieldtype))

	for field in CUSTOM_LOCATION_FIELDS:
		ensure_location_custom_field(field)

	frappe.clear_cache(doctype=LOCATION)
	default_existing_locations_to_active()
	return "Transport Location custom fields installed"


def ensure_location_custom_field(field):
	meta = frappe.get_meta(LOCATION, cached=False)
	existing = meta.get_field(field["fieldname"])
	if existing:
		if existing.fieldtype != field["fieldtype"]:
			frappe.throw(
				_("Transport Location.{0} must be a {1} field.").format(
					field["fieldname"], field["fieldtype"]
				)
			)
		if field.get("options") and existing.options != field["options"]:
			frappe.throw(_("Transport Location.{0} has unexpected options.").format(field["fieldname"]))
		return

	create_custom_field(LOCATION, field)
	frappe.clear_cache(doctype=LOCATION)


def default_existing_locations_to_active():
	if not frappe.get_meta(LOCATION, cached=False).get_field("active"):
		return
	frappe.db.sql("""update `tabTransport Location` set active = 1 where active is null""")


def validate_active_transport_locations(doc, fields):
	"""Reject inactive Transport Location links on operational documents."""
	meta = frappe.get_meta(LOCATION, cached=False)
	if not meta.get_field("active"):
		return

	for fieldname, label in fields:
		location = doc.get(fieldname)
		if not location:
			continue
		active = frappe.db.get_value(LOCATION, location, "active")
		if active is None:
			frappe.throw(_("{0} must be a valid Transport Location.").format(label))
		if not cint(active):
			frappe.throw(_("{0} must be an active Transport Location.").format(label))
