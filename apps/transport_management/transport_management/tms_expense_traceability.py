"""Transport traceability helpers for ERPNext Purchase Invoice rows."""

import frappe
from frappe import _


@frappe.whitelist()
def get_purchase_invoice_item_tms_defaults(transport_trip=None, transport_job=None):
	"""Return TMS references derived from a Transport Trip or Transport Job."""
	if transport_trip:
		return get_defaults_from_trip(transport_trip)
	if transport_job:
		return get_defaults_from_job(transport_job)
	return {}


def normalize_purchase_invoice_tms_references(doc, method=None):
	"""Normalize TMS trace fields on Purchase Invoice Item rows before save/submit."""
	for row in doc.get("items", []):
		normalize_purchase_invoice_item(row)


def normalize_purchase_invoice_item(row):
	if row.get("tms_transport_trip"):
		row.update(get_defaults_from_trip(row.tms_transport_trip))
		return

	if row.get("tms_transport_job"):
		defaults = get_defaults_from_job(row.tms_transport_job)
		validate_or_set_sales_order(row, defaults.get("tms_transport_sales_order"))


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
	defaults["tms_transport_trip"] = trip.name
	defaults["tms_transport_job"] = trip.transport_job

	if trip.execution_source == "OWN":
		defaults["tms_truck"] = trip.vehicle
		defaults["tms_hired_vehicle"] = None
	elif trip.execution_source == "HIRED":
		defaults["tms_truck"] = None
		defaults["tms_hired_vehicle"] = trip.hired_vehicle

	return defaults


def get_defaults_from_job(transport_job):
	job = frappe.db.get_value("Transport Job", transport_job, ["name", "sales_order"], as_dict=True)
	if not job:
		frappe.throw(_("Transport Job {0} does not exist.").format(transport_job))
	return {
		"tms_transport_job": job.name,
		"tms_transport_sales_order": job.sales_order,
	}


def validate_or_set_sales_order(row, sales_order):
	if row.get("tms_transport_sales_order") and sales_order and row.tms_transport_sales_order != sales_order:
		frappe.throw(
			_(
				"Purchase Invoice row {0} links Transport Job {1}, which belongs to Transport Sales Order {2}."
			).format(row.idx, row.tms_transport_job, sales_order)
		)
	if not row.get("tms_transport_sales_order"):
		row.tms_transport_sales_order = sales_order
