"""Tests for Supplier-based transporter party master customizations."""

import unittest

import frappe

from transport_management.party_master import ensure_supplier_transport_fields


class TestPartyMaster(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("party_master_test")
		ensure_supplier_transport_fields()

	def tearDown(self):
		frappe.db.rollback(save_point="party_master_test")

	def make_supplier(self, **values):
		doc = frappe.new_doc("Supplier")
		doc.update({
			"supplier_name": "TMS Test Supplier " + frappe.generate_hash(length=8),
			"supplier_type": "Company",
			"is_transporter": 0,
		})
		doc.update(values)
		return doc

	def test_ordinary_supplier_can_exist_without_transporter_flag(self):
		supplier = self.make_supplier()
		supplier.insert()
		self.assertFalse(supplier.is_transporter)

	def test_transporter_supplier_can_be_created(self):
		supplier = self.make_supplier(
			is_transporter=1,
			transporter_status="Active",
			default_rate_type="Per Trip",
		)
		supplier.insert()
		self.assertTrue(supplier.is_transporter)
		self.assertEqual(supplier.supplier_type, "Company")
		self.assertEqual(supplier.transporter_status, "Active")
		self.assertEqual(supplier.default_rate_type, "Per Trip")

	def test_transporter_custom_field_schema(self):
		meta = frappe.get_meta("Supplier", cached=False)
		status = meta.get_field("transporter_status")
		rate_type = meta.get_field("default_rate_type")
		self.assertEqual(status.fieldtype, "Select")
		self.assertEqual(status.options, "Active\nInactive")
		self.assertEqual(status.default, "Active")
		self.assertEqual(rate_type.fieldtype, "Select")
		self.assertEqual(rate_type.options, "Per Trip\nPer Ton\nPer Route")
		self.assertIsNotNone(meta.get_field("is_transporter"))
		self.assertIsNotNone(meta.get_field("supplier_type"))
		self.assertIsNotNone(meta.get_field("payment_terms"))

	def test_transporter_select_values_are_validated(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_supplier(is_transporter=1, transporter_status="Suspended").insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_supplier(is_transporter=1, default_rate_type="Per Km").insert()

