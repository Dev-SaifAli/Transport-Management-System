# Copyright (c) 2026, Digital Data Enterprises and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe


class TestTransportShipment(unittest.TestCase):
	def shipment(self, **values):
		doc = frappe.new_doc("Transport Shipment")
		doc.update({
			"transport_order": "Test order (not persisted)",
			"quantity": 40.4,
			"loading_site": "ATBT AL TAWEEN",
			"offloading_site": "SAJJA ORYX",
		})
		doc.update(values)
		return doc

	def test_non_positive_and_non_finite_quantity(self):
		for quantity in (None, 0, -1, float("nan"), float("inf")):
			with self.subTest(quantity=quantity):
				with self.assertRaises(frappe.ValidationError):
					self.shipment(quantity=quantity).validate()

	def test_same_locations(self):
		with self.assertRaises(frappe.ValidationError):
			self.shipment(offloading_site="ATBT AL TAWEEN").validate()

	def test_customer_is_fetched_and_multiple_shipments_are_allowed(self):
		shipments = [self.shipment(), self.shipment()]
		with patch("frappe.db.get_value", return_value="ORYX CONCRETE PRODUCT LLC SAJJA"):
			for doc in shipments:
				doc.validate()
				self.assertEqual(doc.customer, "ORYX CONCRETE PRODUCT LLC SAJJA")
				self.assertFalse(doc.trip)

	def test_matching_customer_is_accepted(self):
		doc = self.shipment(customer="ORYX")
		with patch("frappe.db.get_value", return_value="ORYX"):
			doc.validate()

	def test_mismatched_customer_is_rejected(self):
		doc = self.shipment(customer="Different customer")
		with patch("frappe.db.get_value", return_value="ORYX"):
			with self.assertRaises(frappe.ValidationError):
				doc.validate()

	def test_missing_order_or_order_customer_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.shipment(transport_order=None).validate()
		doc = self.shipment()
		with patch("frappe.db.get_value", return_value=None):
			with self.assertRaises(frappe.ValidationError):
				doc.validate()
