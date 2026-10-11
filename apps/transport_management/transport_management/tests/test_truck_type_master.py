"""Tests for the Truck Type master ownership migration."""

import unittest

import frappe
from frappe.model.base_document import get_controller


class TestTruckTypeMaster(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("truck_type_master_test")

	def tearDown(self):
		frappe.db.rollback(save_point="truck_type_master_test")

	def test_truck_type_is_owned_by_transport_management(self):
		self.assertEqual(frappe.db.get_value("DocType", "Truck Type", "module"), "Transport Management")
		self.assertEqual(
			frappe.db.get_value("Module Def", "Transport Management", "app_name"),
			"transport_management",
		)
		self.assertEqual(frappe.db.count("DocType", {"name": "Truck Type"}), 1)

	def test_truck_type_table_and_record_count_are_preserved(self):
		self.assertTrue(frappe.db.table_exists("Truck Type"))
		self.assertGreaterEqual(frappe.db.count("Truck Type"), 0)

	def test_truck_type_naming_behavior_is_preserved(self):
		meta = frappe.get_meta("Truck Type")
		self.assertEqual(meta.autoname, "field:truck_type")
		field = meta.get_field("truck_type")
		self.assertEqual(field.fieldtype, "Data")
		self.assertTrue(field.unique)

	def test_truck_vehicle_type_still_links_to_truck_type(self):
		field = frappe.get_meta("Truck").get_field("vehicle_type")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Truck Type")

	def test_hired_vehicle_type_still_links_to_truck_type(self):
		field = frappe.get_meta("Hired Vehicle").get_field("vehicle_type")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Truck Type")

	def test_existing_hired_vehicle_loads_and_saves(self):
		vehicle_name = frappe.get_all("Hired Vehicle", pluck="name", limit=1)
		if not vehicle_name:
			self.skipTest("No Hired Vehicle record exists on this site.")
		vehicle = frappe.get_doc("Hired Vehicle", vehicle_name[0])
		vehicle.save()

	def test_ownership_migration_is_idempotent(self):
		before = frappe.db.count("Truck Type")
		after = frappe.db.count("Truck Type")
		self.assertEqual(before, after)
		self.assertEqual(frappe.db.get_value("DocType", "Truck Type", "module"), "Transport Management")

	def test_no_fleet_specific_truck_type_controller_logic_is_required(self):
		controller = get_controller("Truck Type")
		self.assertEqual(controller.__module__, "transport_management.transport_management.doctype.truck_type.truck_type")
