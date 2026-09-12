"""Owned Truck customizations owned by transport_management."""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import cint

TRUCK = "Truck"
OWNERSHIP_TYPE_OPTIONS = "OWN"

CUSTOM_TRUCK_FIELDS = (
	{
		"fieldname": "vehicle_type",
		"label": "Vehicle Type",
		"fieldtype": "Link",
		"options": "Truck Type",
		"insert_after": "license_plate",
		"module": "Transport Management",
		"description": "Operational vehicle type owned by transport_management.",
	},
	{
		"fieldname": "capacity",
		"label": "Capacity",
		"fieldtype": "Float",
		"insert_after": "vehicle_type",
		"module": "Transport Management",
		"description": "Operational payload capacity for later trip validation.",
	},
	{
		"fieldname": "capacity_uom",
		"label": "Capacity UOM",
		"fieldtype": "Link",
		"options": "UOM",
		"insert_after": "capacity",
		"module": "Transport Management",
	},
	{
		"fieldname": "ownership_type",
		"label": "Ownership Type",
		"fieldtype": "Select",
		"options": OWNERSHIP_TYPE_OPTIONS,
		"default": "OWN",
		"insert_after": "capacity_uom",
		"module": "Transport Management",
		"description": "This phase supports owned operational fleet records only.",
	},
	{
		"fieldname": "registration_number",
		"label": "Registration Number",
		"fieldtype": "Data",
		"insert_after": "chassis_number",
		"module": "Transport Management",
		"description": "Use only when the registration number differs from the license plate.",
	},
	{
		"fieldname": "registration_expiry",
		"label": "Registration Expiry",
		"fieldtype": "Date",
		"insert_after": "registration_number",
		"module": "Transport Management",
	},
	{
		"fieldname": "insurance_policy_number",
		"label": "Insurance Policy Number",
		"fieldtype": "Data",
		"insert_after": "registration_expiry",
		"module": "Transport Management",
	},
	{
		"fieldname": "insurance_expiry",
		"label": "Insurance Expiry",
		"fieldtype": "Date",
		"insert_after": "insurance_policy_number",
		"module": "Transport Management",
	},
	{
		"fieldname": "erpnext_asset",
		"label": "ERPNext Asset",
		"fieldtype": "Link",
		"options": "Asset",
		"insert_after": "insurance_expiry",
		"module": "Transport Management",
		"description": "Optional link to the financial/depreciation master.",
	},
	{
		"fieldname": "remarks",
		"label": "Remarks",
		"fieldtype": "Small Text",
		"insert_after": "erpnext_asset",
		"module": "Transport Management",
	},
)


def ensure_owned_truck_fields():
	"""Extend Fleet's Truck master without editing Fleet source metadata."""
	meta = frappe.get_meta(TRUCK, cached=False)
	for fieldname, fieldtype in (
		("truck_number", "Data"),
		("license_plate", "Data"),
		("status", "Select"),
		("disabled", "Check"),
		("trans_ms_driver", "Link"),
	):
		field = meta.get_field(fieldname)
		if not field or field.fieldtype != fieldtype:
			frappe.throw(_("Truck.{0} must exist as a {1} field.").format(fieldname, fieldtype))

	for field in CUSTOM_TRUCK_FIELDS:
		ensure_truck_custom_field(field)

	frappe.clear_cache(doctype=TRUCK)
	default_existing_trucks_to_owned()
	return "Owned Truck custom fields installed"


def ensure_truck_custom_field(field):
	meta = frappe.get_meta(TRUCK, cached=False)
	existing = meta.get_field(field["fieldname"])
	if existing:
		if existing.fieldtype != field["fieldtype"]:
			frappe.throw(_("Truck.{0} must be a {1} field.").format(field["fieldname"], field["fieldtype"]))
		if field.get("options") and existing.options != field["options"]:
			frappe.throw(_("Truck.{0} has unexpected options.").format(field["fieldname"]))
		return

	create_custom_field(TRUCK, field)
	frappe.clear_cache(doctype=TRUCK)


def default_existing_trucks_to_owned():
	if not frappe.get_meta(TRUCK, cached=False).get_field("ownership_type"):
		return
	frappe.db.sql("""update `tabTruck` set ownership_type = 'OWN' where ownership_type is null or ownership_type = ''""")


def validate_owned_truck_available(vehicle):
	if not vehicle:
		frappe.throw(_("Vehicle is required for own fleet Transport Trips."))

	truck = frappe.db.get_value(TRUCK, vehicle, ["disabled", "status"], as_dict=True)
	if not truck:
		frappe.throw(_("Vehicle must be a valid Truck."))
	if cint(truck.disabled):
		frappe.throw(_("Disabled Trucks cannot be used for own fleet Transport Trips."))
	if truck.status != "Idle":
		frappe.throw(_("Own fleet Truck must be Idle before it can be used on a Transport Trip."))
