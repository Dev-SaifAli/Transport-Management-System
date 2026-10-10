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
	def autoname(self):
		sync_route_area_zones(self)
		self.rule_name = make_route_rule_name(self)
		self.name = self.rule_name or "New Transport Charge Rule {0}".format(frappe.generate_hash(length=8).upper())

	def before_validate(self):
		sync_route_area_zones(self)
		self.rule_name = make_route_rule_name(self)
		if not self.currency:
			self.currency = DEFAULT_CURRENCY
		if self.active is None:
			self.active = 1
		if self.priority is None:
			self.priority = 100

	def before_save(self):
		sync_route_area_zones(self)
		self.rule_name = make_route_rule_name(self)

	def on_update(self):
		desired_rule_name = make_route_rule_name(self)
		if self.rule_name != desired_rule_name:
			self.db_set("rule_name", desired_rule_name, update_modified=False)
			self.rule_name = desired_rule_name

	def validate(self):
		validate_charge_rule_document(self)


def validate_charge_rule_document(rule):
	validate_rule_charge_lines(rule)
	if rule.valid_from and rule.valid_to and getdate(rule.valid_to) < getdate(rule.valid_from):
		frappe.throw(_("Valid To cannot be before Valid From."))
	if not rule.loading_location and not normalize_zone(rule.loading_area_zone):
		frappe.throw(_("Loading Location or Loading Area / Zone is required."))
	if not rule.unloading_location and not normalize_zone(rule.unloading_area_zone):
		frappe.throw(_("Unloading Location or Unloading Area / Zone is required."))
	if rule.active:
		validate_duplicate_charge_rule(rule)


def sync_route_area_zones(rule):
	if rule.loading_location:
		rule.loading_area_zone = get_location_area_zone(rule.loading_location)
	elif route_location_was_cleared(rule, "loading_location"):
		rule.loading_area_zone = ""
	if rule.unloading_location:
		rule.unloading_area_zone = get_location_area_zone(rule.unloading_location)
	elif route_location_was_cleared(rule, "unloading_location"):
		rule.unloading_area_zone = ""


def get_location_area_zone(location):
	return frappe.db.get_value("Transport Location", location, "area_zone") or ""


def route_location_was_cleared(rule, fieldname):
	if rule.is_new():
		return False
	old_location = frappe.db.get_value(rule.doctype, rule.name, fieldname)
	return bool(old_location and not rule.get(fieldname))


def make_route_rule_name(rule):
	loading = rule.loading_location or rule.loading_area_zone
	unloading = rule.unloading_location or rule.unloading_area_zone
	if not loading or not unloading:
		return ""
	base = _("{0} → {1}").format(loading, unloading)
	if not route_rule_name_exists(base, rule.name):
		return base
	return "{0} | {1}".format(base, frappe.generate_hash(length=6).upper())


def route_rule_name_exists(rule_name, current_name=None):
	filters = {"rule_name": rule_name}
	if current_name:
		filters["name"] = ["!=", current_name]
	return frappe.db.exists("Transport Charge Rule", filters)


def validate_rule_charge_lines(rule):
	lines = get_document_charge_lines(rule)
	if not lines and rule.charge_type:
		if rule.charge_type not in CHARGE_TYPES:
			frappe.throw(_("Invalid Charge Type {0}.").format(rule.charge_type))
		if rule.rate_basis not in RATE_BASIS:
			frappe.throw(_("Invalid Rate Basis {0}.").format(rule.rate_basis))
		if flt(rule.amount, 2) < 0:
			frappe.throw(_("Amount must be greater than or equal to zero."))
		return
	if not lines:
		frappe.throw(_("At least one Charge Line is required."))
	for line in lines:
		if not line.get("active", 1):
			continue
		if line.charge_type not in CHARGE_TYPES:
			frappe.throw(_("Invalid Charge Type {0}.").format(line.charge_type))
		if line.rate_basis not in RATE_BASIS:
			frappe.throw(_("Invalid Rate Basis {0}.").format(line.rate_basis))
		if flt(line.rate, 2) < 0:
			frappe.throw(_("Charge Line Rate must be greater than or equal to zero."))


def get_document_charge_lines(rule):
	return [row for row in rule.get("charge_lines", [])]


def validate_duplicate_charge_rule(rule):
	rows = frappe.get_all(
		"Transport Charge Rule",
		filters={
			"active": 1,
			"priority": rule.priority,
			"name": ["!=", rule.name or ""],
		},
		fields=[
			"name",
			"loading_area_zone",
			"loading_location",
			"unloading_area_zone",
			"unloading_location",
			"valid_from",
			"valid_to",
		],
	)
	for row in rows:
		if (row.loading_location or "") != (rule.loading_location or ""):
			continue
		if normalize_zone(row.loading_area_zone) != normalize_zone(rule.loading_area_zone):
			continue
		if (row.unloading_location or "") != (rule.unloading_location or ""):
			continue
		if normalize_zone(row.unloading_area_zone) != normalize_zone(rule.unloading_area_zone):
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
	unloading_area_zone = frappe.db.get_value("Transport Location", trip.unloading_site, "area_zone")
	matches = []
	for rule in get_candidate_charge_rules(trip):
		match = get_rule_match(rule, trip, loading_area_zone, unloading_area_zone)
		if match:
			matches.append(match)

	selected_rule = select_charge_rule(matches)
	if not selected_rule:
		return []
	return [build_charge_row(selected_rule, line, trip) for line in get_rule_charge_lines(selected_rule)]


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
	if not trip.get("trip_date"):
		missing.append(_("Trip Date"))
	if missing:
		frappe.throw(_("Loading Location, Unloading Location and Trip Date are required before calculating charges."))


def get_candidate_charge_rules(trip):
	return frappe.get_all(
		"Transport Charge Rule",
		filters={
			"active": 1,
		},
		fields=[
			"name",
			"rule_name",
			"charge_type",
			"loading_area_zone",
			"loading_location",
			"unloading_area_zone",
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


def get_rule_match(rule, trip, loading_area_zone, unloading_area_zone=None):
	if rule.valid_from and getdate(rule.valid_from) > getdate(trip.trip_date):
		return None
	if rule.valid_to and getdate(rule.valid_to) < getdate(trip.trip_date):
		return None

	loading_specificity = get_location_match_specificity(
		rule.loading_location,
		rule.loading_area_zone,
		trip.loading_site,
		loading_area_zone,
	)
	unloading_specificity = get_location_match_specificity(
		rule.unloading_location,
		rule.unloading_area_zone,
		trip.unloading_site,
		unloading_area_zone,
	)
	if not loading_specificity or not unloading_specificity:
		return None

	return {
		"rule": rule,
		"specificity": (loading_specificity * 100) + (unloading_specificity * 10),
		"priority": rule.priority or 0,
	}


def get_location_match_specificity(rule_location, rule_area_zone, trip_location, trip_area_zone):
	if rule_location:
		return 2 if rule_location == trip_location else 0
	if normalize_zone(rule_area_zone):
		return 1 if normalize_zone(rule_area_zone) == normalize_zone(trip_area_zone) else 0
	return 0


def select_charge_rule(matches):
	if not matches:
		return None
	matches = sorted(matches, key=lambda row: (row["specificity"], row["priority"]), reverse=True)
	best = matches[0]
	ambiguous = [
		row
		for row in matches
		if row["specificity"] == best["specificity"] and row["priority"] == best["priority"]
	]
	if len(ambiguous) > 1:
		frappe.throw(_("Multiple active Transport Charge Rules match this Trip. Review route rule configuration."))
	return best["rule"]


def get_rule_charge_lines(rule):
	lines = frappe.get_all(
		"Transport Charge Rule Line",
		filters={"parent": rule.name, "parenttype": "Transport Charge Rule", "parentfield": "charge_lines", "active": 1},
		fields=["name", "charge_type", "rate_basis", "rate", "remarks"],
		order_by="idx asc",
	)
	if lines:
		return lines
	if rule.charge_type:
		return [
			frappe._dict({
				"name": None,
				"charge_type": rule.charge_type,
				"rate_basis": rule.rate_basis,
				"rate": rule.amount,
				"remarks": None,
			})
		]
	return []


def build_charge_row(rule, line, trip):
	rate = flt(line.rate, 2)
	quantity = get_charge_quantity(line.rate_basis, trip)
	amount = flt(quantity * rate, 2)
	return {
		"charge_type": line.charge_type,
		"charge_rule": rule.name,
		"charge_rule_line": line.name,
		"rate_basis": line.rate_basis,
		"rate": rate,
		"quantity": quantity,
		"amount": amount,
		"source": RULE_SOURCE,
		"remarks": line.remarks or rule.rule_name or rule.name,
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
		"charge_rule_line": row.get("charge_rule_line"),
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
