"""Fleet compatibility shim; do not edit the upstream Fleet DocType.

Installed by after_migrate so Frappe owns metadata/schema synchronization.
No document validation, mandatory checks, or link checks are overridden here.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

ORDER = "Transportation Order"
FIELDNAME = "assign_transport"
CHILD = "Transport Assignments"


def ensure_assignment_table():
	"""Reuse a compatible field, create a missing field, reject schema conflicts.

	Run through bench migrate on first installation. The shipped Fleet metadata
	contains unrelated legacy Link targets absent from this app stack, which
	Frappe's interactive Custom Field validation rejects outside migration.
	"""
	meta = frappe.get_meta(ORDER, cached=False)
	child = frappe.get_meta(CHILD, cached=False)
	if not child.istable:
		frappe.throw(f"Fleet compatibility: {CHILD} must be a child table.")
	for name, fieldtype, options in (
		("assigned_vehicle", "Link", "Truck"),
		("currency", "Link", "Currency"),
		("container_number", "Data", None),
		("amount", "Float", None),
	):
		df = child.get_field(name)
		if not df or df.fieldtype != fieldtype or (options and df.options != options):
			frappe.throw(f"Fleet compatibility: unexpected {CHILD}.{name} schema; no changes made.")

	field = meta.get_field(FIELDNAME)
	if field:
		if field.fieldtype != "Table" or field.options != CHILD:
			frappe.throw(f"Fleet compatibility: {ORDER}.{FIELDNAME} must be Table → {CHILD}.")
		return "Existing compatible assignment table reused"

	create_custom_field(
		ORDER,
		{
			"fieldname": FIELDNAME,
			"label": "Assign Transport",
			"fieldtype": "Table",
			"options": CHILD,
			"insert_after": "html1",
			"module": "Transport Management",
			"description": "Fleet compatibility shim owned by transport_management. Restores the table expected by Fleet's Transportation Order controller and form.",
		},
	)
	frappe.clear_cache(doctype=ORDER)
	return "Fleet compatibility assignment table created"
