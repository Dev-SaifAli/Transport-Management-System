"""Shared helpers for multi-loading-location TMS documents."""

from math import isfinite

import frappe
from frappe import _
from frappe.utils import flt

from transport_management.location_master import validate_transport_location_usage


def validate_loading_stop_rows(rows, expected_quantity, context_label):
	"""Validate ordered loading stops and return their total quantity."""
	total_quantity = 0
	for row in rows or []:
		if not row.loading_location:
			frappe.throw(_("Loading Location is required on {0} loading stop row {1}.").format(context_label, row.idx))
		validate_transport_location_usage(row.loading_location, {"Loading", "Both"}, _("Loading Location"))

		quantity = flt(row.planned_quantity, 6)
		if not isfinite(quantity) or quantity <= 0:
			frappe.throw(_("Planned Quantity must be greater than zero on {0} loading stop row {1}.").format(
				context_label,
				row.idx,
			))
		total_quantity += quantity

	if rows and flt(total_quantity, 6) != flt(expected_quantity, 6):
		frappe.throw(
			_("{0} loading stop quantities must equal the requested quantity. Stop Total: {1}, Quantity: {2}.").format(
				context_label,
				flt(total_quantity, 6),
				flt(expected_quantity, 6),
			)
		)
	return flt(total_quantity, 6)


def sync_primary_loading_from_stops(doc, fieldname="loading_site"):
	"""Use the first loading stop as the backward-compatible primary loading location."""
	stops = doc.get("loading_stops") or []
	if stops:
		doc.set(fieldname, stops[0].loading_location)


def copy_loading_stops(source_doc, target_doc, target_quantity=None, source_quantity=None):
	target_doc.set("loading_stops", [])
	stops = source_doc.get("loading_stops") or []
	quantities = get_scaled_stop_quantities(stops, target_quantity, source_quantity)
	for index, stop in enumerate(stops):
		target_doc.append("loading_stops", {
			"loading_location": stop.loading_location,
			"planned_quantity": quantities[index],
			"notes": stop.get("notes"),
		})


def get_scaled_stop_quantities(stops, target_quantity=None, source_quantity=None):
	if not target_quantity or not source_quantity or flt(target_quantity, 6) == flt(source_quantity, 6):
		return [stop.planned_quantity for stop in stops]

	scaled_quantities = []
	allocated_quantity = 0
	for index, stop in enumerate(stops):
		if index == len(stops) - 1:
			quantity = flt(flt(target_quantity, 6) - allocated_quantity, 6)
		else:
			quantity = flt(flt(stop.planned_quantity, 6) * flt(target_quantity, 6) / flt(source_quantity, 6), 6)
			allocated_quantity += quantity
		scaled_quantities.append(quantity)
	return scaled_quantities


def serialize_loading_stops(stops, locations=None):
	locations = locations or {}
	return [
		{
			"sequence": stop.idx,
			"loading_location": stop.loading_location,
			"loading_location_name": (locations.get(stop.loading_location) or {}).get("location") or stop.loading_location,
			"loading_area_zone": (locations.get(stop.loading_location) or {}).get("area_zone"),
			"planned_quantity": flt(stop.planned_quantity, 6),
			"notes": stop.get("notes"),
		}
		for stop in stops or []
	]
