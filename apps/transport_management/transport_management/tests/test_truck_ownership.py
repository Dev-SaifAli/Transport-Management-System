"""Tests for Truck ownership migration into transport_management."""

import unittest
from pathlib import Path

import frappe
from frappe.model.base_document import get_controller

from transport_management.demo import setup_demo_data
from transport_management.truck_master import LEGACY_TRUCK_FIELDS, migrate_truck_ownership


class TestTruckOwnershipMigration(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		migrate_truck_ownership()

	def setUp(self):
		frappe.db.savepoint("truck_ownership_test")
		self.demo = setup_demo_data()

	def tearDown(self):
		frappe.db.rollback(save_point="truck_ownership_test")

	def test_truck_belongs_to_transport_management(self):
		self.assertEqual(frappe.db.get_value("DocType", "Truck", "module"), "Transport Management")
		self.assertEqual(get_controller("Truck").__module__, "transport_management.transport_management.doctype.truck.truck")
		self.assertEqual(frappe.db.count("DocType", {"name": "Truck"}), 1)

	def test_table_and_record_are_preserved(self):
		self.assertTrue(frappe.db.table_exists("Truck"))
		self.assertTrue(frappe.db.exists("Truck", "29413-FUJ"))
		truck = frappe.get_doc("Truck", "29413-FUJ")
		self.assertEqual(truck.truck_number, "29413-FUJ")
		self.assertEqual(truck.license_plate, "29413-FUJ")
		self.assertEqual(truck.status, "Idle")
		self.assertFalse(truck.disabled)
		self.assertEqual(truck.ownership_type, "OWN")
		self.assertEqual(truck.fuel_uom, "Litre")

	def test_transport_trip_vehicle_links_remain_valid(self):
		setup_demo_data()
		field = frappe.get_meta("Transport Trip").get_field("vehicle")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Truck")
		for trip in frappe.get_all("Transport Trip", filters={"vehicle": ("is", "set")}, pluck="name"):
			vehicle = frappe.db.get_value("Transport Trip", trip, "vehicle")
			self.assertTrue(frappe.db.exists("Truck", vehicle), trip)

	def test_link_fields_target_current_masters(self):
		meta = frappe.get_meta("Truck")
		self.assertEqual(meta.get_field("trans_ms_driver").options, "Truck Driver")
		self.assertEqual(meta.get_field("vehicle_type").options, "Truck Type")
		self.assertEqual(meta.get_field("capacity_uom").options, "UOM")
		self.assertEqual(meta.get_field("fuel_uom").options, "UOM")
		self.assertEqual(meta.get_field("erpnext_asset").options, "Asset")

	def test_attach_fields_are_native_and_work(self):
		meta = frappe.get_meta("Truck")
		for fieldname in ("registration_attachment", "insurance_attachment", "other_document_attachment"):
			self.assertEqual(meta.get_field(fieldname).fieldtype, "Attach")

		truck = frappe.get_doc("Truck", "29413-FUJ")
		truck.registration_attachment = "/files/ownership-registration.txt"
		truck.insurance_attachment = "/files/ownership-insurance.txt"
		truck.other_document_attachment = "/files/ownership-other.txt"
		truck.save()

		reloaded = frappe.get_doc("Truck", truck.name)
		self.assertEqual(reloaded.registration_attachment, "/files/ownership-registration.txt")
		self.assertEqual(reloaded.insurance_attachment, "/files/ownership-insurance.txt")
		self.assertEqual(reloaded.other_document_attachment, "/files/ownership-other.txt")

	def test_legacy_fields_are_omitted_from_tms_metadata(self):
		meta = frappe.get_meta("Truck")
		for fieldname in LEGACY_TRUCK_FIELDS:
			self.assertFalse(meta.get_field(fieldname), fieldname)

	def test_custom_fields_and_property_setter_are_converted(self):
		self.assertEqual(frappe.db.count("Custom Field", {"dt": "Truck"}), 0)
		self.assertFalse(
			frappe.db.exists(
				"Property Setter",
				{"doc_type": "Truck", "field_name": "fuel_uom", "property": "options"},
			)
		)

	def test_truck_number_defaults_from_license_plate(self):
		hash_value = frappe.generate_hash(length=8)
		truck = frappe.new_doc("Truck")
		truck.update({
			"license_plate": "TMS-DEFAULT-" + hash_value,
			"make": "Test Make",
			"model": "Test Model",
			"manufacturing_year": "2026",
			"acquisition_date": 2026,
			"fuel_type": "Diesel",
			"fuel_uom": "Litre",
			"chassis_number": "CHS-DEFAULT-" + hash_value,
			"status": "Idle",
			"ownership_type": "OWN",
		})
		truck.insert()
		self.assertEqual(truck.truck_number, truck.license_plate)
		self.assertEqual(truck.name, truck.license_plate)

	def test_disabled_status_sets_disabled_flag(self):
		truck = frappe.get_doc("Truck", "29413-FUJ")
		truck.status = "Disabled"
		truck.disabled = 0
		truck.save()
		self.assertTrue(truck.disabled)

	def test_disabled_flag_sets_disabled_status(self):
		truck = frappe.get_doc("Truck", "29413-FUJ")
		truck.disabled = 1
		truck.status = "Idle"
		truck.save()
		self.assertEqual(truck.status, "Disabled")

	def test_active_tms_code_does_not_depend_on_fleet_truck_controller(self):
		app_root = Path(__file__).resolve().parents[1]
		active_files = [
			app_root / "transport_management" / "doctype" / "truck" / "truck.py",
			app_root / "transport_management" / "doctype" / "truck" / "truck.js",
			app_root / "transport_management" / "doctype" / "transport_trip" / "transport_trip.py",
			app_root / "demo.py",
		]
		for path in active_files:
			source = path.read_text()
			for legacy in ("Truck Log", "Fuel Requests", "Manifest", "Document Attachments", "Trailers"):
				self.assertNotIn(legacy, source)
			self.assertNotIn('"Trips"', source)


class TestTruckOwnershipMigrationHelper(unittest.TestCase):
	def test_migration_helper_is_idempotent(self):
		before = frappe.db.count("Truck")
		migrate_truck_ownership()
		migrate_truck_ownership()
		self.assertEqual(frappe.db.count("Truck"), before)
		self.assertEqual(frappe.db.get_value("DocType", "Truck", "module"), "Transport Management")
