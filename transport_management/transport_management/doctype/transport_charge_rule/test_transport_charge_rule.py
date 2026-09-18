import unittest

import frappe
from frappe.utils import add_days, today

from transport_management.transport_management.doctype.transport_charge_rule.transport_charge_rule import (
	calculate_transport_trip_charges,
	populate_transport_trip_charge_rows,
)


class TestTransportChargeRule(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("transport_charge_rule_test")
		self.material = self.make_material()
		self.other_material = self.make_material()
		self.loading = self.make_location("Loading", area_zone="TAWEEN")
		self.other_loading = self.make_location("Loading", area_zone="OTHER")
		self.unloading = self.make_location("Unloading")
		self.other_unloading = self.make_location("Unloading")

	def tearDown(self):
		frappe.db.rollback(save_point="transport_charge_rule_test")

	def make_material(self):
		doc = frappe.new_doc("Cargo Types")
		doc.cargo_name = "TMS CHARGE MATERIAL " + frappe.generate_hash(length=8)
		doc.active = 1
		doc.insert()
		return doc.name

	def make_location(self, usage, area_zone=None):
		doc = frappe.new_doc("Transport Location")
		doc.location = "TMS CHARGE LOC " + frappe.generate_hash(length=8)
		doc.location_usage = usage
		doc.location_type = "Other"
		doc.country = frappe.get_all("Country", pluck="name", limit=1)[0]
		doc.area_zone = area_zone
		doc.active = 1
		doc.insert()
		return doc.name

	def make_rule(self, **values):
		doc = frappe.new_doc("Transport Charge Rule")
		doc.update({
			"rule_name": "TMS CHARGE RULE " + frappe.generate_hash(length=8),
			"charge_type": "RAK Toll",
			"loading_area_zone": "TAWEEN",
			"unloading_location": self.unloading,
			"material": self.material,
			"rate_basis": "Per Trip",
			"amount": 300,
			"currency": "AED",
			"priority": 100,
			"active": 1,
		})
		doc.update(values)
		doc.insert()
		return doc

	def make_trip(self, **values):
		doc = frappe.new_doc("Transport Trip")
		doc.update({
			"trip_date": today(),
			"loading_site": self.loading,
			"unloading_site": self.unloading,
			"material": self.material,
			"planned_quantity": 42,
			"uom": "TON",
		})
		doc.update(values)
		return doc

	def test_exact_loading_location_rule_matches(self):
		rule = self.make_rule(loading_area_zone=None, loading_location=self.loading)
		rows = calculate_transport_trip_charges(self.make_trip())
		self.assertEqual(rows[0]["charge_rule"], rule.name)
		self.assertEqual(rows[0]["amount"], 300)

	def test_area_zone_rule_matches(self):
		rule = self.make_rule()
		rows = calculate_transport_trip_charges(self.make_trip())
		self.assertEqual(rows[0]["charge_rule"], rule.name)

	def test_wrong_loading_area_does_not_match(self):
		self.make_rule()
		rows = calculate_transport_trip_charges(self.make_trip(loading_site=self.other_loading))
		self.assertEqual(rows, [])

	def test_wrong_unloading_location_does_not_match(self):
		self.make_rule()
		rows = calculate_transport_trip_charges(self.make_trip(unloading_site=self.other_unloading))
		self.assertEqual(rows, [])

	def test_wrong_material_does_not_match(self):
		self.make_rule()
		rows = calculate_transport_trip_charges(self.make_trip(material=self.other_material))
		self.assertEqual(rows, [])

	def test_inactive_rule_ignored(self):
		self.make_rule(active=0)
		self.assertEqual(calculate_transport_trip_charges(self.make_trip()), [])

	def test_expired_rule_ignored(self):
		self.make_rule(valid_to=add_days(today(), -1))
		self.assertEqual(calculate_transport_trip_charges(self.make_trip()), [])

	def test_future_rule_ignored(self):
		self.make_rule(valid_from=add_days(today(), 1))
		self.assertEqual(calculate_transport_trip_charges(self.make_trip()), [])

	def test_per_trip_does_not_multiply_by_ton(self):
		self.make_rule(rate_basis="Per Trip", amount=300)
		rows = calculate_transport_trip_charges(self.make_trip(planned_quantity=99))
		self.assertEqual(rows[0]["quantity"], 1)
		self.assertEqual(rows[0]["amount"], 300)

	def test_per_ton_calculates_quantity_times_rate(self):
		self.make_rule(rate_basis="Per TON", amount=7)
		rows = calculate_transport_trip_charges(self.make_trip(planned_quantity=10))
		self.assertEqual(rows[0]["quantity"], 10)
		self.assertEqual(rows[0]["amount"], 70)

	def test_exact_location_rule_overrides_area_rule_for_same_charge_type(self):
		area_rule = self.make_rule(amount=300, priority=500)
		exact_rule = self.make_rule(
			rule_name="TMS EXACT RULE " + frappe.generate_hash(length=8),
			loading_area_zone=None,
			loading_location=self.loading,
			amount=250,
			priority=1,
		)
		rows = calculate_transport_trip_charges(self.make_trip())
		self.assertEqual(rows[0]["charge_rule"], exact_rule.name)
		self.assertNotEqual(rows[0]["charge_rule"], area_rule.name)

	def test_ambiguous_equal_priority_same_type_rules_raise(self):
		self.make_rule(loading_area_zone=None, loading_location=self.loading)
		self.make_rule(
			rule_name="TMS AMBIG RULE " + frappe.generate_hash(length=8),
			loading_location=self.loading,
			loading_area_zone="TAWEEN",
		)
		with self.assertRaises(frappe.ValidationError):
			calculate_transport_trip_charges(self.make_trip())

	def test_recalculation_does_not_duplicate_rule_rows_and_preserves_manual(self):
		trip = self.make_trip()
		trip.append("transport_charges", {
			"charge_type": "Other",
			"rate_basis": "Fixed",
			"rate": 12,
			"quantity": 1,
			"amount": 12,
			"source": "Manual",
		})
		rows = [{
			"charge_type": "RAK Toll",
			"charge_rule": "RULE-1",
			"rate_basis": "Per Trip",
			"rate": 300,
			"quantity": 1,
			"amount": 300,
			"source": "Rule",
		}]
		populate_transport_trip_charge_rows(trip, rows)
		populate_transport_trip_charge_rows(trip, rows)
		self.assertEqual(len(trip.transport_charges), 2)
		self.assertEqual([row.source for row in trip.transport_charges].count("Manual"), 1)
		self.assertEqual([row.source for row in trip.transport_charges].count("Rule"), 1)
		self.assertEqual(trip.rak_toll, 300)
