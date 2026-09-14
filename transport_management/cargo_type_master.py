"""Cargo Types ownership helpers for transport_management."""

import frappe
from frappe import _
from frappe.desk.reportview import get_match_cond
from frappe.modules import reload_doc

CARGO_TYPES = "Cargo Types"
CARGO_TYPE_DETAILS = "Cargo Type Details"
MATERIAL_ALLOWED_TRUCK_TYPE = "Material Allowed Truck Type"
CARGO_MODULE = "Transport Management"
CONFIRMED_MATERIAL_MAPPINGS = {
	"3/4 AGREEGAT(10MM-20MM)": ("TIPPER",),
	"3/16 BLACK SAND FULL WASHED(SAND)": ("TIPPER",),
	"CEMENT": ("TANKER",),
}


def migrate_cargo_types_ownership():
	"""Make Cargo Types and its child table native transport_management DocTypes."""
	reload_doc("transport_management", "doctype", "material_allowed_truck_type", force=True)
	reload_doc("transport_management", "doctype", "cargo_type_details", force=True)
	reload_doc("transport_management", "doctype", "cargo_types", force=True)
	frappe.clear_cache(doctype=MATERIAL_ALLOWED_TRUCK_TYPE)
	frappe.clear_cache(doctype=CARGO_TYPE_DETAILS)
	frappe.clear_cache(doctype=CARGO_TYPES)

	validate_material_allowed_truck_type_metadata()
	validate_cargo_types_metadata()
	validate_cargo_type_details_metadata()

	for doctype in (MATERIAL_ALLOWED_TRUCK_TYPE, CARGO_TYPE_DETAILS, CARGO_TYPES):
		frappe.db.set_value("DocType", doctype, "module", CARGO_MODULE, update_modified=False)
		frappe.clear_cache(doctype=doctype)

	return "Cargo Types ownership migrated"


def validate_cargo_types_metadata():
	meta = frappe.get_meta(CARGO_TYPES, cached=False)
	cargo_name = meta.get_field("cargo_name")
	if not cargo_name or cargo_name.fieldtype != "Data":
		frappe.throw(_("Cargo Types.cargo_name must exist as a Data field."))
	if not cargo_name.unique:
		frappe.throw(_("Cargo Types.cargo_name must remain unique."))

	permits = meta.get_field("permits")
	if not permits or permits.fieldtype != "Table" or permits.options != CARGO_TYPE_DETAILS:
		frappe.throw(_("Cargo Types.permits must remain a Table field linked to Cargo Type Details."))

	active = meta.get_field("active")
	if not active or active.fieldtype != "Check":
		frappe.throw(_("Cargo Types.active must exist as a Check field."))

	allowed_truck_types = meta.get_field("allowed_truck_types")
	if (
		not allowed_truck_types
		or allowed_truck_types.fieldtype != "Table"
		or allowed_truck_types.options != MATERIAL_ALLOWED_TRUCK_TYPE
	):
		frappe.throw(_("Cargo Types.allowed_truck_types must link to Material Allowed Truck Type."))


def validate_material_allowed_truck_type_metadata():
	meta = frappe.get_meta(MATERIAL_ALLOWED_TRUCK_TYPE, cached=False)
	if not meta.istable:
		frappe.throw(_("Material Allowed Truck Type must remain a child table."))

	truck_type = meta.get_field("truck_type")
	if not truck_type or truck_type.fieldtype != "Link" or truck_type.options != "Truck Type":
		frappe.throw(_("Material Allowed Truck Type.truck_type must link to Truck Type."))


def validate_cargo_type_details_metadata():
	meta = frappe.get_meta(CARGO_TYPE_DETAILS, cached=False)
	if not meta.istable:
		frappe.throw(_("Cargo Type Details must remain a child table."))

	expected_fields = {
		"permit_name": ("Data", None),
		"mandatory": ("Check", None),
		"permit_type": (
			"Select",
			"Local Import\nTransit Import\nLocal Export\nTransit Export\nBorder Exit\nBorder Entry",
		),
	}
	for fieldname, (fieldtype, options) in expected_fields.items():
		field = meta.get_field(fieldname)
		if not field or field.fieldtype != fieldtype:
			frappe.throw(_("Cargo Type Details.{0} must exist as a {1} field.").format(fieldname, fieldtype))
		if options and field.options != options:
			frappe.throw(_("Cargo Type Details.{0} has unexpected options.").format(fieldname))


def get_allowed_truck_types(material):
	if not material or not frappe.db.exists(CARGO_TYPES, material):
		return []
	doc = frappe.get_doc(CARGO_TYPES, material)
	return [row.truck_type for row in doc.get("allowed_truck_types", []) if row.truck_type]


def get_effective_material(material=None, transport_job=None, validate_mismatch=False):
	job_material = None
	if transport_job:
		job_material = frappe.db.get_value("Transport Job", transport_job, "material")

	if validate_mismatch and material and job_material and material != job_material:
		frappe.throw(_("Transport Trip Material must match the Transport Job Material."))

	return material or job_material


@frappe.whitelist()
def get_compatible_owned_trucks(material):
	allowed_truck_types = get_allowed_truck_types(material)
	if not allowed_truck_types:
		return []

	return frappe.get_list(
		"Truck",
		filters={
			"vehicle_type": ("in", allowed_truck_types),
			"ownership_type": "OWN",
			"disabled": 0,
			"status": "Idle",
		},
		pluck="name",
	)


@frappe.whitelist()
def get_compatible_hired_vehicles(material=None, transporter=None, transport_job=None):
	effective_material = get_effective_material(material, transport_job)
	allowed_truck_types = get_allowed_truck_types(effective_material)
	if not transporter or not allowed_truck_types:
		return []

	return frappe.get_list(
		"Hired Vehicle",
		filters={
			"transporter": transporter,
			"active": 1,
			"vehicle_type": ("in", allowed_truck_types),
		},
		pluck="name",
	)


def validate_material_allows_owned_truck(material, vehicle):
	if not material or not vehicle:
		return

	allowed_truck_types = get_allowed_truck_types(material)
	if not allowed_truck_types:
		frappe.throw(_("No allowed truck types are configured for material {0}.").format(frappe.bold(material)))

	truck = frappe.db.get_value("Truck", vehicle, ["license_plate", "vehicle_type"], as_dict=True)
	if not truck:
		frappe.throw(_("Vehicle must be a valid Truck."))

	if truck.vehicle_type not in allowed_truck_types:
		frappe.throw(
			_("Truck {0} is not compatible with material {1}. Allowed truck type(s): {2}.").format(
				truck.license_plate or vehicle,
				material,
				", ".join(allowed_truck_types),
			)
		)


def validate_material_allows_hired_vehicle(material, hired_vehicle, transporter=None):
	if not material or not hired_vehicle:
		return

	allowed_truck_types = get_allowed_truck_types(material)
	if not allowed_truck_types:
		frappe.throw(_("No allowed truck types are configured for material {0}.").format(frappe.bold(material)))

	vehicle = frappe.db.get_value(
		"Hired Vehicle",
		hired_vehicle,
		["plate_number", "transporter", "active", "vehicle_type"],
		as_dict=True,
	)
	if not vehicle:
		frappe.throw(_("Hired Vehicle must exist."))

	if transporter and vehicle.transporter != transporter:
		frappe.throw(_("Hired Vehicle must belong to the selected Transporter."))
	if not vehicle.active:
		frappe.throw(_("Inactive Hired Vehicles cannot be used on Transport Trips."))
	if not vehicle.vehicle_type or vehicle.vehicle_type not in allowed_truck_types:
		frappe.throw(
			_("Hired Vehicle {0} is not compatible with material {1}. Allowed truck type(s): {2}.").format(
				vehicle.plate_number or hired_vehicle,
				material,
				", ".join(allowed_truck_types),
			)
		)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def compatible_owned_truck_query(doctype, txt, searchfield, start, page_len, filters):
	material = (filters or {}).get("material")
	allowed_truck_types = get_allowed_truck_types(material)
	if not allowed_truck_types:
		return []

	return frappe.db.sql(
		f"""
		select name, license_plate, vehicle_type
		from `tabTruck`
		where {searchfield} like %(txt)s
			and vehicle_type in %(allowed_truck_types)s
			and ownership_type = 'OWN'
			and disabled = 0
			and status = 'Idle'
			{get_match_cond("Truck")}
		order by
			case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end,
			name
		limit %(page_len)s offset %(start)s
		""",
		{
			"txt": f"%{txt}%",
			"_txt": txt.replace("%", ""),
			"allowed_truck_types": tuple(allowed_truck_types),
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def compatible_hired_vehicle_query(doctype, txt, searchfield, start, page_len, filters):
	filters = filters or {}
	material = get_effective_material(filters.get("material"), filters.get("transport_job"))
	transporter = filters.get("transporter")
	allowed_truck_types = get_allowed_truck_types(material)
	if not transporter or not allowed_truck_types:
		return []

	return frappe.db.sql(
		f"""
		select name, plate_number, vehicle_type
		from `tabHired Vehicle`
		where {searchfield} like %(txt)s
			and transporter = %(transporter)s
			and active = 1
			and vehicle_type in %(allowed_truck_types)s
			{get_match_cond("Hired Vehicle")}
		order by
			case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end,
			name
		limit %(page_len)s offset %(start)s
		""",
		{
			"txt": f"%{txt}%",
			"_txt": txt.replace("%", ""),
			"transporter": transporter,
			"allowed_truck_types": tuple(allowed_truck_types),
			"start": start,
			"page_len": page_len,
		},
	)


def ensure_confirmed_material_mappings():
	"""Create/update only confirmed AL RANA material compatibility mappings."""
	ensure_required_truck_types()
	for material_name, truck_types in CONFIRMED_MATERIAL_MAPPINGS.items():
		doc = _get_or_create_material(material_name)
		changed = False
		if not doc.active:
			doc.active = 1
			changed = True
		existing = {row.truck_type for row in doc.get("allowed_truck_types", []) if row.truck_type}
		for truck_type in truck_types:
			if truck_type not in existing:
				doc.append("allowed_truck_types", {"truck_type": truck_type})
				existing.add(truck_type)
				changed = True
		if changed:
			doc.save()
	return "Confirmed material mappings configured"


def ensure_required_truck_types():
	for truck_type in ("TIPPER", "TANKER"):
		if frappe.db.exists("Truck Type", truck_type):
			continue
		doc = frappe.new_doc("Truck Type")
		doc.truck_type = truck_type
		doc.insert()


def _get_or_create_material(material_name):
	if frappe.db.exists(CARGO_TYPES, material_name):
		return frappe.get_doc(CARGO_TYPES, material_name)
	doc = frappe.new_doc(CARGO_TYPES)
	doc.cargo_name = material_name
	doc.active = 1
	doc.insert()
	return doc
