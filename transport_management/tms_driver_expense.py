"""Driver expense foundation helpers using standard HRMS Expense Claim."""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

EXPENSE_CLAIM_DETAIL = "Expense Claim Detail"
EXPENSE_CLAIM_TYPES = ("Toll", "Parking", "Fuel", "Other")

EXPENSE_CLAIM_DETAIL_FIELDS = (
	{
		"fieldname": "transport_trip",
		"label": "Transport Trip",
		"fieldtype": "Link",
		"options": "Transport Trip",
		"insert_after": "project",
		"module": "Transport Management",
	},
	{
		"fieldname": "transport_job",
		"label": "Transport Job",
		"fieldtype": "Link",
		"options": "Transport Job",
		"insert_after": "transport_trip",
		"module": "Transport Management",
	},
	{
		"fieldname": "truck",
		"label": "Truck",
		"fieldtype": "Link",
		"options": "Truck",
		"insert_after": "transport_job",
		"module": "Transport Management",
	},
	{
		"fieldname": "hired_vehicle",
		"label": "Hired Vehicle",
		"fieldtype": "Link",
		"options": "Hired Vehicle",
		"insert_after": "truck",
		"module": "Transport Management",
	},
)


def ensure_driver_expense_foundation():
	ensure_expense_claim_types()
	ensure_expense_claim_detail_fields()
	frappe.clear_cache(doctype=EXPENSE_CLAIM_DETAIL)


def ensure_expense_claim_types():
	for expense_type in EXPENSE_CLAIM_TYPES:
		if frappe.db.exists("Expense Claim Type", expense_type):
			continue
		frappe.get_doc({
			"doctype": "Expense Claim Type",
			"expense_type": expense_type,
			"description": _("TMS driver expense category."),
		}).insert(ignore_permissions=True)


def ensure_expense_claim_detail_fields():
	for field in EXPENSE_CLAIM_DETAIL_FIELDS:
		ensure_custom_field(EXPENSE_CLAIM_DETAIL, field)


def ensure_custom_field(doctype, field):
	custom_field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]})
	if not custom_field:
		create_custom_field(doctype, field)
		return

	updates = {
		key: value
		for key, value in field.items()
		if key in {"label", "fieldtype", "options", "insert_after", "module"}
	}
	frappe.db.set_value("Custom Field", custom_field, updates, update_modified=False)


@frappe.whitelist()
def get_expense_claim_detail_tms_defaults(transport_trip=None, transport_job=None):
	if transport_trip:
		return get_defaults_from_trip(transport_trip)
	if transport_job:
		return get_defaults_from_job(transport_job)
	return {}


def normalize_expense_claim_tms_references(doc, method=None):
	for row in doc.get("expenses", []):
		normalize_expense_claim_detail(row)


def normalize_expense_claim_detail(row):
	if row.get("transport_trip"):
		row.update(get_defaults_from_trip(row.transport_trip))
		return

	if row.get("transport_job"):
		defaults = get_defaults_from_job(row.transport_job)
		row.transport_job = defaults["transport_job"]

	if row.get("truck") and row.get("hired_vehicle"):
		frappe.throw(
			_("Expense Claim row {0} cannot reference both Truck and Hired Vehicle.").format(row.idx)
		)


def get_defaults_from_trip(transport_trip):
	trip = frappe.db.get_value(
		"Transport Trip",
		transport_trip,
		["name", "transport_job", "execution_source", "vehicle", "hired_vehicle"],
		as_dict=True,
	)
	if not trip:
		frappe.throw(_("Transport Trip {0} does not exist.").format(transport_trip))
	if not trip.transport_job:
		frappe.throw(_("Transport Trip {0} is not linked to a Transport Job.").format(transport_trip))

	defaults = get_defaults_from_job(trip.transport_job)
	defaults["transport_trip"] = trip.name
	defaults["transport_job"] = trip.transport_job

	if trip.execution_source == "OWN":
		defaults["truck"] = trip.vehicle
		defaults["hired_vehicle"] = None
	elif trip.execution_source == "HIRED":
		defaults["truck"] = None
		defaults["hired_vehicle"] = trip.hired_vehicle
	else:
		defaults["truck"] = None
		defaults["hired_vehicle"] = None

	return defaults


def get_defaults_from_job(transport_job):
	job = frappe.db.get_value("Transport Job", transport_job, ["name"], as_dict=True)
	if not job:
		frappe.throw(_("Transport Job {0} does not exist.").format(transport_job))
	return {"transport_job": job.name}


def get_driver_employee_mapping_summary():
	drivers = frappe.get_all("Truck Driver", fields=["name", "full_name", "employee"], order_by="name")
	unmapped = [driver for driver in drivers if not driver.employee]
	return {
		"total_drivers": len(drivers),
		"mapped_drivers": len(drivers) - len(unmapped),
		"unmapped_drivers": unmapped,
	}
