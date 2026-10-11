"""Tests for Cargo Types ownership migration."""

import unittest

import frappe
from frappe.model.base_document import get_controller

from transport_management.cargo_type_master import (
	CONFIRMED_MATERIAL_MAPPINGS,
	get_allowed_truck_types,
)
from transport_management.demo import setup_demo_data


class TestCargoTypeMaster(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("cargo_type_master_test")
		self.demo = setup_demo_data()
		self.job = frappe.get_doc("Transport Job", self.demo["transport_job"])

	def tearDown(self):
		frappe.db.rollback(save_point="cargo_type_master_test")

	def test_cargo_types_is_owned_by_transport_management(self):
		self.assertEqual(frappe.db.get_value("DocType", "Cargo Types", "module"), "Transport Management")
		self.assertEqual(
			frappe.db.get_value("Module Def", "Transport Management", "app_name"),
			"transport_management",
		)
		self.assertEqual(frappe.db.count("DocType", {"name": "Cargo Types"}), 1)

	def test_cargo_type_details_is_owned_by_transport_management(self):
		self.assertEqual(frappe.db.get_value("DocType", "Cargo Type Details", "module"), "Transport Management")
		self.assertTrue(frappe.get_meta("Cargo Type Details").istable)
		self.assertEqual(frappe.db.count("DocType", {"name": "Cargo Type Details"}), 1)

	def test_material_allowed_truck_type_is_owned_by_transport_management(self):
		self.assertEqual(
			frappe.db.get_value("DocType", "Material Allowed Truck Type", "module"),
			"Transport Management",
		)
		self.assertTrue(frappe.get_meta("Material Allowed Truck Type").istable)
		self.assertEqual(frappe.db.count("DocType", {"name": "Material Allowed Truck Type"}), 1)

	def test_tables_and_records_are_preserved(self):
		self.assertTrue(frappe.db.table_exists("Cargo Types"))
		self.assertTrue(frappe.db.table_exists("Cargo Type Details"))
		self.assertTrue(frappe.db.table_exists("Material Allowed Truck Type"))
		self.assertTrue(frappe.db.exists("Cargo Types", "3/4 Aggregate"))
		self.assertGreaterEqual(frappe.db.count("Cargo Types"), 1)
		self.assertGreaterEqual(frappe.db.count("Cargo Type Details"), 0)

	def test_cargo_types_naming_and_child_table_are_preserved(self):
		meta = frappe.get_meta("Cargo Types")
		self.assertEqual(meta.autoname, "field:cargo_name")
		cargo_name = meta.get_field("cargo_name")
		self.assertEqual(cargo_name.fieldtype, "Data")
		self.assertEqual(cargo_name.label, "Material Name")
		self.assertTrue(cargo_name.unique)
		active = meta.get_field("active")
		self.assertEqual(active.fieldtype, "Check")
		allowed_truck_types = meta.get_field("allowed_truck_types")
		self.assertEqual(allowed_truck_types.fieldtype, "Table")
		self.assertEqual(allowed_truck_types.options, "Material Allowed Truck Type")
		permits = meta.get_field("permits")
		self.assertEqual(permits.fieldtype, "Table")
		self.assertEqual(permits.options, "Cargo Type Details")

	def test_material_allowed_truck_type_schema(self):
		meta = frappe.get_meta("Material Allowed Truck Type")
		self.assertEqual(meta.autoname, "autoincrement")
		self.assertTrue(meta.istable)
		truck_type = meta.get_field("truck_type")
		self.assertEqual(truck_type.fieldtype, "Link")
		self.assertEqual(truck_type.options, "Truck Type")

	def test_cargo_type_details_schema_is_preserved(self):
		meta = frappe.get_meta("Cargo Type Details")
		self.assertEqual(meta.autoname, "autoincrement")
		self.assertEqual(meta.get_field("permit_name").fieldtype, "Data")
		self.assertEqual(meta.get_field("mandatory").fieldtype, "Check")
		self.assertEqual(meta.get_field("permit_type").fieldtype, "Select")

	def test_transport_job_material_still_resolves_and_saves(self):
		self.assertTrue(frappe.db.exists("Cargo Types", self.job.material))
		self.assertEqual(frappe.get_meta("Transport Job").get_field("material").options, "Cargo Types")
		self.job.save()

	def test_transport_trip_material_still_resolves_and_saves(self):
		self.assertEqual(frappe.get_meta("Transport Trip").get_field("material").options, "Cargo Types")
		for trip_name in self.demo["transport_trips"]:
			trip = frappe.get_doc("Transport Trip", trip_name)
			self.assertTrue(frappe.db.exists("Cargo Types", trip.material))
			trip.save()

	def test_no_duplicate_cargo_doctype_metadata_exists(self):
		self.assertEqual(frappe.db.count("DocType", {"name": "Cargo Types"}), 1)
		self.assertEqual(frappe.db.count("DocType", {"name": "Cargo Type Details"}), 1)
		self.assertEqual(frappe.db.count("DocType", {"name": "Material Allowed Truck Type"}), 1)

	def test_no_active_tms_code_depends_on_fleet_cargo_controller_logic(self):
		self.assertEqual(
			get_controller("Cargo Types").__module__,
			"transport_management.transport_management.doctype.cargo_types.cargo_types",
		)
		self.assertEqual(
			get_controller("Cargo Type Details").__module__,
			"transport_management.transport_management.doctype.cargo_type_details.cargo_type_details",
		)
		self.assertEqual(
			get_controller("Material Allowed Truck Type").__module__,
			"transport_management.transport_management.doctype.material_allowed_truck_type.material_allowed_truck_type",
		)

	def test_confirmed_material_mappings_are_configured(self):
		for material, truck_types in CONFIRMED_MATERIAL_MAPPINGS.items():
			self.assertTrue(frappe.db.exists("Cargo Types", material))
			self.assertEqual(sorted(get_allowed_truck_types(material)), sorted(truck_types))

	def test_existing_aggregate_material_is_not_renamed_or_merged(self):
		self.assertTrue(frappe.db.exists("Cargo Types", "3/4 Aggregate"))
		self.assertTrue(frappe.db.exists("Cargo Types", "3/4 AGREEGAT(10MM-20MM)"))
		self.assertNotEqual("3/4 Aggregate", "3/4 AGREEGAT(10MM-20MM)")


class TestCargoTypeOwnershipMigration(unittest.TestCase):
	def test_ownership_migration_is_idempotent(self):
		from transport_management.cargo_type_master import migrate_cargo_types_ownership

		before_parent = frappe.db.count("Cargo Types")
		before_child = frappe.db.count("Cargo Type Details")
		before_allowed = frappe.db.count("Material Allowed Truck Type")
		migrate_cargo_types_ownership()
		migrate_cargo_types_ownership()
		self.assertEqual(frappe.db.count("Cargo Types"), before_parent)
		self.assertEqual(frappe.db.count("Cargo Type Details"), before_child)
		self.assertEqual(frappe.db.count("Material Allowed Truck Type"), before_allowed)
		self.assertEqual(frappe.db.get_value("DocType", "Cargo Types", "module"), "Transport Management")
		self.assertEqual(frappe.db.get_value("DocType", "Cargo Type Details", "module"), "Transport Management")
		self.assertEqual(frappe.db.get_value("DocType", "Material Allowed Truck Type", "module"), "Transport Management")
