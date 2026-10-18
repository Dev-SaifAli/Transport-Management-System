"""Focused tests for Transport Quotation lifecycle and validation."""

import unittest

import frappe
from frappe.modules import reload_doc

from transport_management.demo import setup_demo_data


class TestTransportQuotation(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_quotation_material", force=True)
		reload_doc("transport_management", "doctype", "transport_quotation_location", force=True)
		reload_doc("transport_management", "doctype", "transport_quotation_rate", force=True)
		reload_doc("transport_management", "doctype", "transport_quotation", force=True)

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("transport_quotation_test")
		self.demo = setup_demo_data()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="transport_quotation_test")

	def make_quotation(self, complete=False, **values):
		doc = frappe.new_doc("Transport Quotation")
		doc.update({
			"quotation_date": "2026-01-01",
			"valid_until": "2026-01-31",
			"service_period_from": "2026-10-01",
			"service_period_to": "2026-12-31",
			"customer": self.demo["customer"],
			"currency": "AED",
		})
		if complete:
			doc.append("materials", {"material": self.demo["material"]})
			doc.append("locations", {
				"material": self.demo["material"],
				"location_role": "Loading",
				"location": self.demo["loading_site"],
			})
			doc.append("locations", {
				"material": self.demo["material"],
				"location_role": "Destination",
				"location": self.demo["offloading_site"],
			})
			doc.append("rates", {
				"material": self.demo["material"],
				"loading_location": self.demo["loading_site"],
				"unloading_location": self.demo["offloading_site"],
				"rate": 25,
				"effective_from": "2026-10-01",
				"effective_to": "2026-12-31",
				"rate_group": "Group 1",
			})
			doc.customer_approval_date = "2026-01-15"
		doc.update(values)
		return doc

	def test_new_quotation_defaults_to_aed_and_draft(self):
		doc = self.make_quotation()
		doc.insert()

		self.assertEqual(doc.currency, "AED")
		self.assertEqual(doc.status, "Draft")
		self.assertEqual(doc.docstatus, 0)

	def test_acceptance_validity_and_service_period_are_independent(self):
		doc = self.make_quotation(complete=True)
		doc.insert()

		self.assertLess(doc.valid_until, doc.service_period_from)

	def test_acceptance_validity_cannot_precede_quotation_date(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_quotation(valid_until="2025-12-31").insert()

	def test_service_period_requires_both_dates_and_valid_order(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_quotation(service_period_to=None).insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_quotation(
				service_period_from="2026-12-31",
				service_period_to="2026-10-01",
			).insert()

	def test_currency_is_fixed_to_aed(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_quotation(currency="USD").insert()

	def test_estimates_are_optional_and_non_binding_but_cannot_be_negative(self):
		doc = self.make_quotation(estimated_quantity=5000, estimated_trips=180)
		doc.insert()
		self.assertEqual(doc.estimated_quantity, 5000)
		self.assertEqual(doc.estimated_trips, 180)

		with self.assertRaises(frappe.ValidationError):
			self.make_quotation(estimated_quantity=-1).insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_quotation(estimated_trips="not-a-number").insert()

	def test_duplicate_materials_are_rejected(self):
		doc = self.make_quotation(complete=True)
		doc.append("materials", {"material": self.demo["material"]})

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_location_role_must_match_transport_location_usage(self):
		doc = self.make_quotation(complete=True)
		doc.locations[0].location = self.demo["offloading_site"]

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_rates_must_reference_selected_material_and_locations(self):
		doc = self.make_quotation(complete=True)
		doc.locations = []
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_overlapping_effective_periods_for_a_route_are_rejected(self):
		doc = self.make_quotation(complete=True, service_period_to="2027-02-01")
		doc.append("rates", {
			"material": self.demo["material"],
			"loading_location": self.demo["loading_site"],
			"unloading_location": self.demo["offloading_site"],
			"rate": 30,
			"effective_from": "2026-12-31",
			"effective_to": "2027-02-01",
		})

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_adjacent_non_overlapping_rate_periods_are_valid(self):
		doc = self.make_quotation(complete=True)
		doc.rates[0].effective_to = "2026-11-15"
		doc.append("rates", {
			"material": self.demo["material"],
			"loading_location": self.demo["loading_site"],
			"unloading_location": self.demo["offloading_site"],
			"rate": 30,
			"effective_from": "2026-11-16",
			"effective_to": "2026-12-31",
		})
		doc.insert()
		self.assertEqual(len(doc.rates), 2)

	def test_rate_period_must_be_inside_service_period_when_given(self):
		doc = self.make_quotation(complete=True)
		doc.rates[0].effective_to = "2027-01-01"

		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_approval_requires_complete_rate_schedule(self):
		doc = self.make_quotation(complete=True)
		doc.rates = []

		with self.assertRaises(frappe.ValidationError):
			doc.insert()
			doc.submit()

	def test_approval_requires_valid_customer_approval_date(self):
		doc = self.make_quotation(complete=True, customer_approval_date=None)
		doc.insert()

		with self.assertRaises(frappe.ValidationError):
			doc.submit()

	def test_approval_sets_approved_status_and_freezes_commercial_terms(self):
		doc = self.make_quotation(complete=True)
		doc.insert()
		doc.submit()

		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.status, "Approved")

		doc.valid_until = "2026-02-15"
		with self.assertRaises(frappe.exceptions.UpdateAfterSubmitError):
			doc.save()

	def test_approval_permissions_are_limited_to_authorized_roles(self):
		permissions = {row.role: row for row in frappe.get_meta("Transport Quotation").permissions}

		self.assertTrue(permissions["Transport Manager"].submit)
		self.assertTrue(permissions["Transport Admin"].submit)
		self.assertTrue(permissions["System Manager"].submit)
		self.assertFalse(permissions["TMS Trip Data Entry"].get("submit"))
		self.assertFalse(permissions["TMS + Expense Data Entry"].get("submit"))

	def test_unauthorized_user_cannot_record_customer_approval(self):
		doc = self.make_quotation(complete=True)
		doc.insert()

		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				doc.submit()
		finally:
			frappe.set_user("Administrator")

	def test_controlled_revision_requires_approved_source_and_reason(self):
		source = self.make_quotation(complete=True)
		source.insert()
		source.submit()

		revision = self.make_quotation(revision_of=source.name, revision_reason="Updated rates")
		revision.insert()
		self.assertEqual(revision.revision_of, source.name)

		with self.assertRaises(frappe.ValidationError):
			self.make_quotation(revision_of=source.name).insert()

	def test_revision_of_draft_quotation_is_rejected(self):
		source = self.make_quotation()
		source.insert()

		with self.assertRaises(frappe.ValidationError):
			self.make_quotation(revision_of=source.name, revision_reason="Update").insert()
