"""Transport Location customizations owned by transport_management."""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.modules import reload_doc
from frappe.utils import cint

LOCATION = "Transport Location"
LOCATION_TYPE_OPTIONS = "Customer Site\nSupplier Site\nPlant\nYard\nWarehouse\nPort\nOther"
LOCATION_USAGE_OPTIONS = "Loading\nUnloading\nBoth"
LOCATION_MODULE = "Transport Management"

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
		"hidden": 1,
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
		"fieldname": "area_zone",
		"label": "Area / Zone",
		"fieldtype": "Data",
		"insert_after": "city",
		"module": "Transport Management",
	},
	{
		"fieldname": "latitude",
		"label": "Latitude",
		"fieldtype": "Float",
		"insert_after": "area_zone",
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
	"""Ensure Transport Location has the fields required by TMS."""
	meta = frappe.get_meta(LOCATION, cached=False)
	for fieldname, fieldtype in (("location", "Data"), ("country", "Link")):
		field = meta.get_field(fieldname)
		if not field or field.fieldtype != fieldtype:
			frappe.throw(_("Transport Location.{0} must exist as a {1} field.").format(fieldname, fieldtype))

	for field in CUSTOM_LOCATION_FIELDS:
		ensure_location_custom_field(field)

	frappe.clear_cache(doctype=LOCATION)
	default_existing_locations_to_active()
	default_existing_location_usage_from_links()
	return "Transport Location custom fields installed"


def migrate_transport_location_ownership():
	"""Make Transport Location a native transport_management DocType.

	Reloading here keeps Transport Management as the effective owner during
	migrate and after legacy Fleet removal.
	"""
	reload_doc("transport_management", "doctype", "transport_location", force=True)
	frappe.clear_cache(doctype=LOCATION)

	standard_fields = get_standard_location_fieldnames()
	missing = [field["fieldname"] for field in CUSTOM_LOCATION_FIELDS if field["fieldname"] not in standard_fields]
	for fieldname in ("location_usage", "location_map_section", "map_html", "notes_section"):
		if fieldname not in standard_fields:
			missing.append(fieldname)
	if missing:
		frappe.throw(_("Transport Location standard fields were not synced: {0}").format(", ".join(missing)))

	delete_legacy_location_custom_fields()
	frappe.db.set_value("DocType", LOCATION, "module", LOCATION_MODULE, update_modified=False)
	frappe.clear_cache(doctype=LOCATION)
	default_existing_locations_to_active()
	default_existing_location_usage_from_links()
	return "Transport Location ownership migrated"


def get_standard_location_fieldnames():
	return {
		row.fieldname
		for row in frappe.get_all(
			"DocField",
			filters={"parent": LOCATION},
			fields=["fieldname"],
		)
	}


def delete_legacy_location_custom_fields():
	for field in CUSTOM_LOCATION_FIELDS:
		name = frappe.db.get_value("Custom Field", {"dt": LOCATION, "fieldname": field["fieldname"]})
		if name:
			frappe.delete_doc("Custom Field", name, force=True)


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
		if "hidden" in field and cint(existing.hidden) != cint(field["hidden"]):
			frappe.db.set_value("DocField", existing.name, "hidden", cint(field["hidden"]), update_modified=False)
		return

	create_custom_field(LOCATION, field)
	frappe.clear_cache(doctype=LOCATION)


def default_existing_locations_to_active():
	if not frappe.get_meta(LOCATION, cached=False).get_field("active"):
		return
	frappe.db.sql("""update `tabTransport Location` set active = 1 where active is null""")


def default_existing_location_usage_from_links():
	"""Classify existing locations only when usage is proven by current TMS links."""
	if not frappe.get_meta(LOCATION, cached=False).get_field("location_usage"):
		return

	loading_locations = set()
	unloading_locations = set()
	for doctype in ("Transport Job", "Transport Trip"):
		if not frappe.db.exists("DocType", doctype):
			continue
		for row in frappe.get_all(
			doctype,
			fields=["loading_site", "unloading_site"],
			filters={"docstatus": ("<", 2)},
		):
			if row.loading_site:
				loading_locations.add(row.loading_site)
			if row.unloading_site:
				unloading_locations.add(row.unloading_site)

	for location in frappe.get_all(LOCATION, pluck="name"):
		if frappe.db.get_value(LOCATION, location, "location_usage"):
			continue
		is_loading = location in loading_locations
		is_unloading = location in unloading_locations
		if is_loading and is_unloading:
			frappe.db.set_value(LOCATION, location, "location_usage", "Both", update_modified=False)
		elif is_loading:
			frappe.db.set_value(LOCATION, location, "location_usage", "Loading", update_modified=False)
		elif is_unloading:
			frappe.db.set_value(LOCATION, location, "location_usage", "Unloading", update_modified=False)


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


def validate_transport_location_usage(location, allowed_usages, label):
	"""Reject Transport Locations that are inactive or not intended for the given usage."""
	if not location:
		return

	values = frappe.db.get_value(
		LOCATION,
		location,
		["location_usage", "active"],
		as_dict=True,
	)
	if not values:
		frappe.throw(_("{0} must be a valid Transport Location.").format(label))
	if not cint(values.active):
		frappe.throw(_("{0} must be an active Transport Location.").format(label))
	if values.location_usage not in allowed_usages:
		frappe.throw(
			_("{0} must have Location Usage {1}.").format(
				label,
				_(" or ").join(sorted(allowed_usages)),
			)
		)
