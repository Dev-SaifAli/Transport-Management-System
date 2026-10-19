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

	def test_send_to_customer_transitions_draft_to_pending_approval_and_persists(self):
		from transport_management.transport_management.doctype.transport_quotation.transport_quotation import (
			send_quotation_to_customer,
		)

		doc = self.make_quotation(complete=True, customer_approval_date=None)
		doc.insert()
		self.assertEqual(doc.status, "Draft")

		res = send_quotation_to_customer(doc.name, "Sent via email to customer")
		self.assertEqual(res["status"], "Pending Approval")

		reloaded = frappe.get_doc("Transport Quotation", doc.name)
		self.assertEqual(reloaded.status, "Pending Approval")
		self.assertEqual(reloaded.docstatus, 0)
		self.assertEqual(reloaded.customer_approval_notes, "Sent via email to customer")

	def test_reject_quotation_records_rejection_without_submitting_or_cancelling_draft(self):
		from transport_management.transport_management.doctype.transport_quotation.transport_quotation import (
			approve_quotation,
			reject_quotation,
			send_quotation_to_customer,
		)

		doc = self.make_quotation(complete=True, customer_approval_date=None)
		doc.insert()
		send_quotation_to_customer(doc.name, "Sent for review")

		res = reject_quotation(doc.name, "Customer rejected rates due to budget")
		self.assertEqual(res["status"], "Rejected")
		self.assertEqual(res["docstatus"], 0)

		reloaded = frappe.get_doc("Transport Quotation", doc.name)
		self.assertEqual(reloaded.status, "Rejected")
		self.assertEqual(reloaded.docstatus, 0)
		self.assertEqual(reloaded.customer_approval_notes, "Customer rejected rates due to budget")

		# Rejected quotation is immutable and cannot be edited or approved
		reloaded.remarks = "Attempted edit after rejection"
		with self.assertRaises(frappe.ValidationError):
			reloaded.save()

		with self.assertRaises(frappe.ValidationError):
			approve_quotation(doc.name, "2026-01-15", "PO-123", "Late approval")

	def test_approve_quotation_from_pending_approval_submits_and_locks(self):
		from transport_management.transport_management.doctype.transport_quotation.transport_quotation import (
			approve_quotation,
			reject_quotation,
			send_quotation_to_customer,
		)

		doc = self.make_quotation(complete=True, customer_approval_date=None)
		doc.insert()
		send_quotation_to_customer(doc.name, "Awaiting PO")

		res = approve_quotation(doc.name, "2026-01-15", "PO-REF-900", "Customer signed rate sheet")
		self.assertEqual(res["status"], "Approved")
		self.assertEqual(res["docstatus"], 1)

		reloaded = frappe.get_doc("Transport Quotation", doc.name)
		self.assertEqual(reloaded.status, "Approved")
		self.assertEqual(reloaded.docstatus, 1)
		self.assertEqual(str(reloaded.customer_approval_date), "2026-01-15")
		self.assertEqual(reloaded.customer_approval_reference, "PO-REF-900")

		# Approved quotation cannot be rejected
		with self.assertRaises(frappe.ValidationError):
			reject_quotation(doc.name, "Attempted rejection after approval")

	def test_unauthorized_user_cannot_send_approve_or_reject_quotation(self):
		from transport_management.transport_management.doctype.transport_quotation.transport_quotation import (
			approve_quotation,
			reject_quotation,
			send_quotation_to_customer,
		)

		doc = self.make_quotation(complete=True, customer_approval_date=None)
		doc.insert()

		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				send_quotation_to_customer(doc.name, "Unauthorized send")
			with self.assertRaises(frappe.PermissionError):
				approve_quotation(doc.name, "2026-01-15", "REF", "Unauthorized approve")
			with self.assertRaises(frappe.PermissionError):
				reject_quotation(doc.name, "Unauthorized reject")
		finally:
			frappe.set_user("Administrator")

	def test_unapproved_pending_or_rejected_quotations_cannot_create_sales_order(self):
		from transport_management.transport_management.doctype.transport_quotation.transport_quotation import (
			reject_quotation,
			send_quotation_to_customer,
		)
		from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
			create_quotation_transport_sales_order,
		)

		doc = self.make_quotation(complete=True, customer_approval_date=None)
		doc.insert()

		# 1. Draft cannot create Sales Order
		with self.assertRaises(frappe.ValidationError):
			create_quotation_transport_sales_order(doc.name)

		# 2. Pending Approval cannot create Sales Order
		send_quotation_to_customer(doc.name, "Sent to customer")
		with self.assertRaises(frappe.ValidationError):
			create_quotation_transport_sales_order(doc.name)

		# 3. Rejected cannot create Sales Order
		reject_quotation(doc.name, "Rejected by customer")
		with self.assertRaises(frappe.ValidationError):
			create_quotation_transport_sales_order(doc.name)

	def test_get_quotation_list_with_summaries_returns_materials_locations_and_rates(self):
		from transport_management.transport_management.doctype.transport_quotation.transport_quotation import (
			get_quotation_list_with_summaries,
		)

		doc = self.make_quotation(complete=True)
		doc.insert()

		rows = get_quotation_list_with_summaries(limit_page_length=50)
		matched = next((r for r in rows if r["name"] == doc.name), None)
		self.assertIsNotNone(matched)
		self.assertEqual(len(matched["materials"]), 1)
		self.assertEqual(matched["materials"][0]["material"], self.demo["material"])
		self.assertEqual(len(matched["locations"]), 2)
		self.assertEqual(len(matched["rates"]), 1)

