"""Tests for the TMS demo layer on Fleet's Transportation Order."""

import unittest

import frappe

from transport_management.transport_order_ui import ensure_transportation_order_ui


class TestTransportationOrderUI(unittest.TestCase):
	def test_demo_reference_fields_and_layout_are_installed(self):
		ensure_transportation_order_ui()
		meta = frappe.get_meta("Transportation Order", cached=False)

		for fieldname, label in (
			("tms_do_number", "DO Number"),
			("tms_customer_do", "Customer DO"),
			("tms_sale_order_route_reference", "Sale Order / Route Reference"),
			("tms_fnrc", "FNRC"),
		):
			field = meta.get_field(fieldname)
			self.assertIsNotNone(field)
			self.assertEqual(field.fieldtype, "Data")
			self.assertEqual(field.label, label)

		self.assertEqual(meta.get_field("order_details_section").label, "Transport Order Details")
		self.assertEqual(meta.get_field("cargo_location_city").label, "Loading Site")
		self.assertFalse(meta.get_field("cargo_location_city").hidden)
		self.assertFalse(meta.get_field("cargo_destination_city").hidden)
		self.assertFalse(meta.get_field("goods_description").hidden)
		self.assertFalse(meta.get_field("amount").hidden)
		self.assertFalse(meta.get_field("unit").hidden)
		self.assertTrue(meta.get_field("cargo").hidden)
		self.assertTrue(meta.get_field("assign_transport").hidden)
		self.assertTrue(meta.get_field("create_invoice").hidden)

	def test_demo_ui_installer_is_idempotent(self):
		before_fields = frappe.db.count("Custom Field", {"dt": "Transportation Order"})
		before_setters = frappe.db.count("Property Setter", {"doc_type": "Transportation Order"})
		ensure_transportation_order_ui()
		ensure_transportation_order_ui()
		self.assertEqual(before_fields, frappe.db.count("Custom Field", {"dt": "Transportation Order"}))
		self.assertEqual(before_setters, frappe.db.count("Property Setter", {"doc_type": "Transportation Order"}))
