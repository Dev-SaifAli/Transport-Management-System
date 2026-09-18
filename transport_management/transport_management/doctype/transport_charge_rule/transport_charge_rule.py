# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

CHARGE_TYPES = {"RAK Toll", "Sharjah Toll", "FNRC / Extra Charge", "Other"}
RATE_BASIS = {"Per Trip", "Per TON", "Fixed"}
DEFAULT_CURRENCY = "AED"
RULE_SOURCE = "Rule"
MANUAL_SOURCE = "Manual"
LEGACY_CHARGE_FIELDS = {
	"RAK Toll": "rak_toll",
	"Sharjah Toll": "sharjah_toll",
	"FNRC / Extra Charge": "fnrc_extra_charge",
}


class TransportChargeRule(Document):
	def before_validate(self):
		if not self.currency:
			self.currency = DEFAULT_CURRENCY
		if self.active is None:
			self.active = 1
		if self.priority is None:
			self.priority = 100

	def validate(self):
		validate_charge_rule_document(self)


def validate_charge_rule_document(rule):
	if rule.charge_type not in CHARGE_TYPES:
		frappe.throw(_("Invalid Charge Type {0}.").format(rule.charge_type))
	if rule.rate_basis not in RATE_BASIS:
		frappe.throw(_("Invalid Rate Basis {0}.").format(rule.rate_basis))
	if flt(rule.amount, 2) < 0:
		frappe.throw(_("Amount must be greater than or equal to zero."))
	if rule.valid_from and rule.valid_to and getdate(rule.valid_to) < getdate(rule.valid_from):
		frappe.throw(_("Valid To cannot be before Valid From."))
	if not rule.loading_location and not normalize_zone(rule.loading_area_zone):
		frappe.throw(_("Loading Location or Loading Area / Zone is required."))
	if not rule.unloading_location:
		frappe.throw(_("Unloading Location is required."))
	if rule.active:
		validate_duplicate_charge_rule(rule)


def validate_duplicate_charge_rule(rule):
	rows = frappe.get_all(
		"Transport Charge Rule",
		filters={
			"charge_type": rule.charge_type,
			"unloading_location": rule.unloading_location,
			"active": 1,
			"priority": rule.priority,
			"name": ["!=", rule.name or ""],
		},
		fields=[
			"name",
			"loading_area_zone",
			"loading_location",
			"material",
			"valid_from",
			"valid_to",
		],
	)
	for row in rows:
		if (row.loading_location or "") != (rule.loading_location or ""):
			continue
		if normalize_zone(row.loading_area_zone) != normalize_zone(rule.loading_area_zone):
			continue
		if (row.material or "") != (rule.material or ""):
			continue
		if date_ranges_overlap(rule.valid_from, rule.valid_to, row.valid_from, row.valid_to):
			frappe.throw(
				_("Transport Charge Rule {0} conflicts with active rule {1}.").format(rule.rule_name or rule.name, row.name)
			)


def date_ranges_overlap(start_a, end_a, start_b, end_b):
	start_a = getdate(start_a) if start_a else None
	end_a = getdate(end_a) if end_a else None
	start_b = getdate(start_b) if start_b else None
	end_b = getdate(end_b) if end_b else None
	return (not end_a or not start_b or end_a >= start_b) and (not end_b or not start_a or end_b >= start_a)


def calculate_transport_trip_charges(trip):
	trip = get_trip_doc(trip)
	validate_trip_charge_inputs(trip)

	loading_area_zone = frappe.db.get_value("Transport Location", trip.loading_site, "area_zone")
	matches = []
	for rule in get_candidate_charge_rules(trip):
		match = get_rule_match(rule, trip, loading_area_zone)
		if match:
			matches.append(match)

	selected_rules = select_charge_rules(matches)
	return [build_charge_row(rule, trip) for rule in selected_rules]


def get_trip_doc(trip):
	if isinstance(trip, str):
		return frappe.get_doc("Transport Trip", trip)
	if isinstance(trip, dict):
		return frappe._dict(trip)
	return trip


def validate_trip_charge_inputs(trip):
	missing = []
	if not trip.get("loading_site"):
		missing.append(_("Loading Location"))
	if not trip.get("unloading_site"):
		missing.append(_("Unloading Location"))
	if not trip.get("material"):
		missing.append(_("Material"))
	if not trip.get("trip_date"):
		missing.append(_("Trip Date"))
	if missing:
		frappe.throw(_("Loading Location, Unloading Location, Material and Trip Date are required before calculating charges."))


def get_candidate_charge_rules(trip):
	return frappe.get_all(
		"Transport Charge Rule",
		filters={
			"active": 1,
			"unloading_location": trip.unloading_site,
		},
		fields=[
			"name",
			"rule_name",
			"charge_type",
			"loading_area_zone",
			"loading_location",
			"unloading_location",
			"material",
			"rate_basis",
			"amount",
			"currency",
			"valid_from",
			"valid_to",
			"priority",
		],
	)


def get_rule_match(rule, trip, loading_area_zone):
	if rule.valid_from and getdate(rule.valid_from) > getdate(trip.trip_date):
		return None
	if rule.valid_to and getdate(rule.valid_to) < getdate(trip.trip_date):
		return None
	if rule.material and rule.material != trip.material:
		return None

	has_material = bool(rule.material)
	if rule.loading_location and rule.loading_location == trip.loading_site:
		return {
			"rule": rule,
			"specificity": 400 if has_material else 200,
			"priority": rule.priority or 0,
		}

	if not rule.loading_location and normalize_zone(rule.loading_area_zone) == normalize_zone(loading_area_zone):
		return {
			"rule": rule,
			"specificity": 300 if has_material else 100,
			"priority": rule.priority or 0,
		}

	return None


def select_charge_rules(matches):
	by_charge_type = {}
	for match in matches:
		by_charge_type.setdefault(match["rule"].charge_type, []).append(match)

	selected = []
	for charge_type, charge_matches in by_charge_type.items():
		charge_matches = sorted(charge_matches, key=lambda row: (row["specificity"], row["priority"]), reverse=True)
		best = charge_matches[0]
		ambiguous = [
			row
			for row in charge_matches
			if row["specificity"] == best["specificity"] and row["priority"] == best["priority"]
		]
		if len(ambiguous) > 1:
			frappe.throw(
				_("Multiple active {0} rules match this Trip. Review Transport Charge Rule configuration.").format(
					charge_type
				)
			)
		selected.append(best["rule"])

	return sorted(selected, key=lambda rule: (rule.charge_type, rule.priority or 0, rule.name))


def build_charge_row(rule, trip):
	rate = flt(rule.amount, 2)
	quantity = get_charge_quantity(rule.rate_basis, trip)
	amount = flt(quantity * rate, 2)
	return {
		"charge_type": rule.charge_type,
		"charge_rule": rule.name,
		"rate_basis": rule.rate_basis,
		"rate": rate,
		"quantity": quantity,
		"amount": amount,
		"source": RULE_SOURCE,
		"remarks": rule.rule_name or rule.name,
	}


def get_charge_quantity(rate_basis, trip):
	if rate_basis in {"Per Trip", "Fixed"}:
		return 1
	quantity = trip.get("delivered_quantity") or trip.get("loaded_quantity") or trip.get("actual_quantity") or trip.get("planned_quantity")
	return flt(quantity, 6)


def apply_transport_trip_charges(transport_trip):
	trip = frappe.get_doc("Transport Trip", transport_trip)
	rows = calculate_transport_trip_charges(trip)
	populate_transport_trip_charge_rows(trip, rows)
	trip.save()
	return {
		"transport_trip": trip.name,
		"charges": rows,
		"totals": get_transport_trip_charge_totals(trip),
	}


def populate_transport_trip_charge_rows(trip, calculated_rows):
	manual_rows = [get_child_charge_row_values(row) for row in trip.get("transport_charges", []) if row.source == MANUAL_SOURCE]
	trip.set("transport_charges", [])
	for row in manual_rows:
		trip.append("transport_charges", row)
	for row in calculated_rows:
		trip.append("transport_charges", row)
	sync_legacy_charge_totals(trip, force=True)


def get_child_charge_row_values(row):
	return {
		"charge_type": row.charge_type,
		"charge_rule": row.charge_rule,
		"rate_basis": row.rate_basis,
		"rate": flt(row.rate, 2),
		"quantity": flt(row.quantity, 6),
		"amount": flt(row.amount, 2),
		"source": row.source or MANUAL_SOURCE,
		"remarks": row.remarks,
	}


def sync_legacy_charge_totals(trip, force=False):
	if not force and not trip.get("transport_charges"):
		return
	totals = get_transport_trip_charge_totals(trip)
	trip.rak_toll = totals.get("rak_toll", 0)
	trip.sharjah_toll = totals.get("sharjah_toll", 0)
	trip.fnrc_extra_charge = totals.get("fnrc_extra_charge", 0)
	trip.toll_applicable = 1 if trip.rak_toll or trip.sharjah_toll else 0


def get_transport_trip_charge_totals(trip):
	charge_rows = get_charge_rows(trip)
	if not charge_rows:
		return {}

	totals = {
		"rak_toll": 0,
		"sharjah_toll": 0,
		"fnrc_extra_charge": 0,
		"other_charge": 0,
		"total_extra_charges": 0,
	}
	for row in charge_rows:
		amount = flt(row.get("amount"), 2)
		fieldname = LEGACY_CHARGE_FIELDS.get(row.get("charge_type"))
		if fieldname:
			totals[fieldname] = flt(totals[fieldname] + amount, 2)
		else:
			totals["other_charge"] = flt(totals["other_charge"] + amount, 2)
		totals["total_extra_charges"] = flt(totals["total_extra_charges"] + amount, 2)
	return totals


def get_charge_rows(trip):
	if isinstance(trip, str):
		return frappe.get_all(
			"Transport Trip Charge",
			filters={"parent": trip, "parenttype": "Transport Trip", "parentfield": "transport_charges"},
			fields=["charge_type", "amount"],
		)
	return [{"charge_type": row.charge_type, "amount": row.amount} for row in trip.get("transport_charges", [])]


def normalize_zone(value):
	return (value or "").strip().casefold()
