"""Demo-friendly Transportation Order customizations owned by this app."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

ORDER = "Transportation Order"

CUSTOM_FIELDS = (
	("tms_do_number", "DO Number", "unit"),
	("tms_customer_do", "Customer DO", "tms_do_number"),
	("tms_sale_order_route_reference", "Sale Order / Route Reference", "tms_customer_do"),
	("tms_fnrc", "FNRC", "tms_sale_order_route_reference"),
)

PROPERTY_SETTERS = (
	("order_details_section", "label", "Transport Order Details", "Data"),
	("date", "label", "Date", "Data"),
	("customer", "label", "Customer", "Data"),
	("company", "label", "Company", "Data"),
	("cargo_location_city", "label", "Loading Site", "Data"),
	("cargo_destination_city", "label", "Offloading Site", "Data"),
	("goods_description", "label", "Material", "Data"),
	("amount", "label", "Ordered Quantity", "Data"),
	("unit", "label", "Order UOM", "Data"),
	("special_instruction_to_transporter", "label", "Special Instructions", "Data"),
	("date", "insert_after", "order_details_section", "Data"),
	("customer", "insert_after", "date", "Data"),
	("company", "insert_after", "customer", "Data"),
	("cargo_location_city", "insert_after", "company", "Data"),
	("cargo_destination_city", "insert_after", "cargo_location_city", "Data"),
	("goods_description", "insert_after", "cargo_destination_city", "Data"),
	("amount", "insert_after", "goods_description", "Data"),
	("unit", "insert_after", "amount", "Data"),
	("special_instruction_to_transporter", "insert_after", "tms_fnrc", "Data"),
	("cargo_location_city", "hidden", 0, "Check"),
	("cargo_destination_city", "hidden", 0, "Check"),
	("goods_description", "hidden", 0, "Check"),
	("amount", "hidden", 0, "Check"),
	("unit", "hidden", 0, "Check"),
	("consignee_and_shipper_section", "hidden", 1, "Check"),
	("border_and_transportation_instruction_section", "hidden", 1, "Check"),
	("cargo_information_section", "hidden", 1, "Check"),
	("cargo_location_country", "hidden", 1, "Check"),
	("cargo_destination_country", "hidden", 1, "Check"),
	("transport_type", "hidden", 1, "Check"),
	("amended_from", "hidden", 1, "Check"),
	("cargo_type", "hidden", 1, "Check"),
	("cargo_description", "hidden", 1, "Check"),
	("cargo", "hidden", 1, "Check"),
	("html1", "hidden", 1, "Check"),
	("assign_transport", "hidden", 1, "Check"),
	("total_assigned", "hidden", 1, "Check"),
	("create_invoice", "hidden", 1, "Check"),
	("references_section", "hidden", 1, "Check"),
	("version", "hidden", 1, "Check"),
)


def ensure_transportation_order_ui():
	"""Create the light TMS demo layer without editing Fleet source files."""
	for fieldname, label, insert_after in CUSTOM_FIELDS:
		ensure_data_custom_field(fieldname, label, insert_after)

	for fieldname, prop, value, property_type in PROPERTY_SETTERS:
		ensure_property_setter(fieldname, prop, value, property_type)

	frappe.clear_cache(doctype=ORDER)
	return "Transportation Order demo UI customizations installed"


def ensure_data_custom_field(fieldname, label, insert_after):
	meta = frappe.get_meta(ORDER, cached=False)
	field = meta.get_field(fieldname)
	if field:
		if field.fieldtype != "Data":
			frappe.throw(f"TMS demo UI: {ORDER}.{fieldname} must be a Data field.")
		return

	create_custom_field(
		ORDER,
		{
			"fieldname": fieldname,
			"label": label,
			"fieldtype": "Data",
			"insert_after": insert_after,
			"module": "Transport Management",
			"description": "TMS demo reference field owned by transport_management.",
		},
	)
	frappe.clear_cache(doctype=ORDER)


def ensure_property_setter(fieldname, prop, value, property_type):
	value = str(value)
	filters = {
		"doc_type": ORDER,
		"doctype_or_field": "DocField",
		"field_name": fieldname,
		"property": prop,
	}
	name = frappe.db.get_value("Property Setter", filters)
	if name:
		frappe.db.set_value(
			"Property Setter",
			name,
			{
				"value": value,
				"property_type": property_type,
				"module": "Transport Management",
				"is_system_generated": 1,
			},
			update_modified=False,
		)
		return

	doc = frappe.get_doc({
		"doctype": "Property Setter",
		"doctype_or_field": "DocField",
		"doc_type": ORDER,
		"field_name": fieldname,
		"property": prop,
		"value": value,
		"property_type": property_type,
		"module": "Transport Management",
		"is_system_generated": 1,
	})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_version = True
	doc.insert()
