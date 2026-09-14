"""Owned Truck customizations owned by transport_management."""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.modules import reload_doc
from frappe.utils import cint

TRUCK = "Truck"
TRUCK_MODULE = "Transport Management"
OWNERSHIP_TYPE_OPTIONS = "OWN"
FUEL_UOM_PROPERTY_SETTER = "Truck-fuel_uom-options"
LEGACY_TRUCK_FIELDS = (
	"trans_ms_current_trip",
	"trans_ms_default_trailer",
	"trans_ms_maintain_stock",
	"trans_ms_fuel_warehouse",
	"vehicle_documents",
	"located_yard",
)

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
		"fieldname": "registration_attachment",
		"label": "Registration Document",
		"fieldtype": "Attach",
		"insert_after": "registration_expiry",
		"module": "Transport Management",
	},
	{
		"fieldname": "insurance_policy_number",
		"label": "Insurance Policy Number",
		"fieldtype": "Data",
		"insert_after": "registration_attachment",
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
		"fieldname": "insurance_attachment",
		"label": "Insurance Document",
		"fieldtype": "Attach",
		"insert_after": "insurance_expiry",
		"module": "Transport Management",
	},
	{
		"fieldname": "other_document_attachment",
		"label": "Other Document",
		"fieldtype": "Attach",
		"insert_after": "insurance_attachment",
		"module": "Transport Management",
	},
	{
		"fieldname": "erpnext_asset",
		"label": "ERPNext Asset",
		"fieldtype": "Link",
		"options": "Asset",
		"insert_after": "other_document_attachment",
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
	ensure_truck_fuel_uom_uses_erpnext_uom()

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


def migrate_truck_ownership():
	"""Make Truck a native transport_management DocType without moving data."""
	validate_no_live_legacy_truck_data()
	record_count = frappe.db.count(TRUCK)

	ensure_truck_fuel_uom_uses_erpnext_uom()
	reload_doc("transport_management", "doctype", "truck", force=True)
	frappe.clear_cache(doctype=TRUCK)

	validate_tms_truck_metadata()
	delete_legacy_truck_custom_fields()
	delete_truck_fuel_uom_property_setter_if_native()
	frappe.db.set_value("DocType", TRUCK, "module", TRUCK_MODULE, update_modified=False)
	frappe.clear_cache(doctype=TRUCK)
	default_existing_trucks_to_owned()

	if frappe.db.count(TRUCK) != record_count:
		frappe.throw(_("Truck ownership migration changed the Truck record count."))

	return "Truck ownership migrated"


def validate_tms_truck_metadata():
	meta = frappe.get_meta(TRUCK, cached=False)
	if meta.module != TRUCK_MODULE:
		frappe.throw(_("Truck must be owned by Transport Management."))

	expected_fields = {
		"truck_number": ("Data", None),
		"license_plate": ("Data", None),
		"make": ("Data", None),
		"model": ("Data", None),
		"manufacturing_year": ("Data", None),
		"acquisition_date": ("Int", None),
		"status": ("Select", "Idle\nUnder Maintenance\nOn Trip\nDisabled"),
		"disabled": ("Check", None),
		"trans_ms_driver": ("Link", "Truck Driver"),
		"trans_ms__driver_name": ("Data", None),
		"odometer_value": ("Data", None),
		"acquisition_odometer_reading": ("Data", None),
		"engine_number": ("Data", None),
		"chassis_number": ("Data", None),
		"fuel_type": ("Select", "Petrol\nDiesel"),
		"fuel_uom": ("Link", "UOM"),
		"vehicle_type": ("Link", "Truck Type"),
		"capacity": ("Float", None),
		"capacity_uom": ("Link", "UOM"),
		"ownership_type": ("Select", OWNERSHIP_TYPE_OPTIONS),
		"registration_number": ("Data", None),
		"registration_expiry": ("Date", None),
		"registration_attachment": ("Attach", None),
		"insurance_policy_number": ("Data", None),
		"insurance_expiry": ("Date", None),
		"insurance_attachment": ("Attach", None),
		"other_document_attachment": ("Attach", None),
		"erpnext_asset": ("Link", "Asset"),
		"remarks": ("Small Text", None),
	}
	for fieldname, (fieldtype, options) in expected_fields.items():
		field = meta.get_field(fieldname)
		if not field or field.fieldtype != fieldtype:
			frappe.throw(_("Truck.{0} must exist as a {1} field.").format(fieldname, fieldtype))
		if options and field.options != options:
			frappe.throw(_("Truck.{0} has unexpected options.").format(fieldname))

	for fieldname in LEGACY_TRUCK_FIELDS:
		if meta.get_field(fieldname):
			frappe.throw(_("Legacy Truck field {0} is not part of the TMS Truck metadata.").format(fieldname))


def validate_no_live_legacy_truck_data():
	if not frappe.db.table_exists(TRUCK):
		return

	legacy_conditions = []
	for fieldname in LEGACY_TRUCK_FIELDS:
		if frappe.db.has_column(TRUCK, fieldname):
			if fieldname == "trans_ms_maintain_stock":
				legacy_conditions.append(f"ifnull({fieldname}, 0) != 0")
			else:
				legacy_conditions.append(f"ifnull({fieldname}, '') != ''")

	if not legacy_conditions:
		return

	count = frappe.db.sql(
		f"""select count(*) from `tabTruck` where {" or ".join(legacy_conditions)}""",
		as_list=True,
	)[0][0]
	if count:
		frappe.throw(_("Truck legacy Fleet fields contain live data; review before migration."))


def delete_legacy_truck_custom_fields():
	for field in CUSTOM_TRUCK_FIELDS:
		name = frappe.db.get_value("Custom Field", {"dt": TRUCK, "fieldname": field["fieldname"]})
		if name:
			frappe.delete_doc("Custom Field", name, force=True)


def delete_truck_fuel_uom_property_setter_if_native():
	field = frappe.get_meta(TRUCK, cached=False).get_field("fuel_uom")
	if field and field.options == "UOM":
		name = frappe.db.exists("Property Setter", FUEL_UOM_PROPERTY_SETTER)
		if name:
			frappe.delete_doc("Property Setter", name, force=True)
		frappe.clear_cache(doctype=TRUCK)


def ensure_truck_fuel_uom_uses_erpnext_uom():
	"""Point Truck.fuel_uom at ERPNext UOM without editing Fleet source JSON."""
	meta = frappe.get_meta(TRUCK, cached=False)
	field = meta.get_field("fuel_uom")
	if not field or field.fieldtype != "Link":
		frappe.throw(_("Truck.fuel_uom must exist as a Link field."))

	ensure_erpnext_uom_for_truck_fuel_values()

	native_options = frappe.db.get_value("DocField", {"parent": TRUCK, "fieldname": "fuel_uom"}, "options")
	if native_options == "UOM":
		delete_truck_fuel_uom_property_setter_if_native()
		return

	property_setter = frappe.db.exists("Property Setter", FUEL_UOM_PROPERTY_SETTER)
	if property_setter:
		frappe.db.set_value(
			"Property Setter",
			property_setter,
			{
				"value": "UOM",
				"property_type": "Small Text",
				"module": "Transport Management",
				"is_system_generated": 1,
			},
		)
	else:
		frappe.make_property_setter(
			{
				"doctype": TRUCK,
				"fieldname": "fuel_uom",
				"property": "options",
				"value": "UOM",
				"property_type": "Small Text",
			},
			module="Transport Management",
		)

	frappe.clear_cache(doctype=TRUCK)
	field = frappe.get_meta(TRUCK, cached=False).get_field("fuel_uom")
	if field.options != "UOM":
		frappe.throw(_("Truck.fuel_uom must link to ERPNext UOM."))


def ensure_erpnext_uom_for_truck_fuel_values():
	values = frappe.get_all(
		TRUCK,
		filters={"fuel_uom": ("not in", ("", None))},
		pluck="fuel_uom",
		distinct=True,
	)
	missing_values = []
	for value in values:
		if frappe.db.exists("UOM", value):
			if frappe.db.get_value("UOM", value, "enabled") == 0:
				frappe.throw(_("ERPNext UOM {0} is disabled; enable it before Fuel UOM migration.").format(value))
			continue
		if value == "Litre":
			uom = frappe.new_doc("UOM")
			uom.uom_name = "Litre"
			uom.enabled = 1
			uom.insert()
			continue
		missing_values.append(value)

	if missing_values:
		frappe.throw(
			_("Truck fuel UOM values missing in ERPNext UOM: {0}").format(", ".join(sorted(missing_values)))
		)


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
