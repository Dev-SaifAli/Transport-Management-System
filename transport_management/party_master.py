"""Party master customizations owned by transport_management."""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

SUPPLIER = "Supplier"

CUSTOM_SUPPLIER_FIELDS = (
	{
		"fieldname": "transporter_status",
		"label": "Transporter Status",
		"fieldtype": "Select",
		"options": "Active\nInactive",
		"default": "Active",
		"insert_after": "is_transporter",
		"depends_on": "eval:doc.is_transporter",
		"module": "Transport Management",
		"description": "Transporter operational status owned by transport_management.",
	},
	{
		"fieldname": "default_rate_type",
		"label": "Default Rate Type",
		"fieldtype": "Select",
		"options": "Per Trip\nPer Ton\nPer Route",
		"insert_after": "transporter_status",
		"depends_on": "eval:doc.is_transporter",
		"module": "Transport Management",
		"description": "Default transporter commercial rate basis; no rate automation is implemented.",
	},
)


def ensure_supplier_transport_fields():
	"""Install Supplier transporter attributes without editing ERPNext metadata."""
	meta = frappe.get_meta(SUPPLIER, cached=False)
	is_transporter = meta.get_field("is_transporter")
	if not is_transporter or is_transporter.fieldtype != "Check":
		frappe.throw(_("Supplier.is_transporter must exist as a Check field."))

	for field in CUSTOM_SUPPLIER_FIELDS:
		ensure_supplier_custom_field(field)

	frappe.clear_cache(doctype=SUPPLIER)
	return "Supplier transporter fields installed"


def ensure_supplier_custom_field(field):
	meta = frappe.get_meta(SUPPLIER, cached=False)
	existing = meta.get_field(field["fieldname"])
	if existing:
		if existing.fieldtype != field["fieldtype"]:
			frappe.throw(
				_("Supplier.{0} must be a {1} field.").format(field["fieldname"], field["fieldtype"])
			)
		if field.get("options") and existing.options != field["options"]:
			frappe.throw(_("Supplier.{0} has unexpected options.").format(field["fieldname"]))
		return

	create_custom_field(SUPPLIER, field)
	frappe.clear_cache(doctype=SUPPLIER)
