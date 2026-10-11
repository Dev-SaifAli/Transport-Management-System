# Copyright (c) 2026, Digital Data Enterprises and Contributors
# See license.txt

import unittest

import frappe


class TestRetiredTransportShipment(unittest.TestCase):
	def test_deprecated_transport_shipment_doctype_is_preserved(self):
		meta = frappe.get_meta("Transport Shipment")
		self.assertEqual(meta.name, "Transport Shipment")
		self.assertIn("Retired", meta.description)

	def test_legacy_references_are_plain_data(self):
		meta = frappe.get_meta("Transport Shipment")
		fields = {field.fieldname: field for field in meta.fields}
		self.assertEqual(fields["transport_order"].fieldtype, "Data")
		self.assertFalse(fields["transport_order"].options)
		self.assertEqual(fields["trip"].fieldtype, "Data")
		self.assertFalse(fields["trip"].options)

	def test_existing_historical_record_is_preserved(self):
		shipment = frappe.get_doc("Transport Shipment", "SHP-2026-00002")
		self.assertEqual(shipment.transport_order, "TORD-2026-00001")
		self.assertFalse(shipment.trip)
		self.assertEqual(shipment.docstatus, 1)

	def test_no_new_transport_shipment_workflow_is_active(self):
		doc = frappe.new_doc("Transport Shipment")
		doc.update({
			"date": "2026-09-10",
			"transport_order": "LEGACY-ONLY",
			"customer": "ORYX CONCRETE PRODUCT LLC SAJJA",
			"loading_site": "ATBT AL TAWEEN",
			"offloading_site": "SAJJA ORYX",
			"material": "3/4 Aggregate",
			"quantity": 1,
			"uom": "Tonne",
		})
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_runtime_no_longer_reads_transportation_order(self):
		source = (
			frappe.get_app_path(
				"transport_management",
				"transport_management",
				"doctype",
				"transport_shipment",
				"transport_shipment.py",
			)
		)
		with open(source) as handle:
			self.assertNotIn("Transportation Order", handle.read())

	def test_client_no_longer_reads_transportation_order(self):
		source = (
			frappe.get_app_path(
				"transport_management",
				"transport_management",
				"doctype",
				"transport_shipment",
				"transport_shipment.js",
			)
		)
		with open(source) as handle:
			self.assertNotIn("Transportation Order", handle.read())

	def test_existing_transport_shipment_data_is_not_touched_by_demo_setup(self):
		from transport_management.demo import setup_demo_data

		frappe.db.savepoint("retired_transport_shipment_test")
		try:
			before = frappe.db.count("Transport Shipment")
			setup_demo_data()
			self.assertEqual(frappe.db.count("Transport Shipment"), before)
		finally:
			frappe.db.rollback(save_point="retired_transport_shipment_test")

	def test_stale_transportation_order_customizations_are_removed(self):
		from transport_management.legacy_fleet_cleanup import retire_transport_shipment_and_cleanup_fleet_customizations

		retire_transport_shipment_and_cleanup_fleet_customizations()
		self.assertEqual(frappe.db.count("Custom Field", {"dt": "Transportation Order", "module": "Transport Management"}), 0)
		self.assertEqual(frappe.db.count("Property Setter", {"doc_type": "Transportation Order", "module": "Transport Management"}), 0)
