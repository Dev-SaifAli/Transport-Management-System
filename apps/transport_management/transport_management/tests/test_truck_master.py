"""Tests for the owned Truck master extension."""

import unittest
from pathlib import Path

import frappe

from transport_management.demo import setup_demo_data
from transport_management.truck_master import ensure_owned_truck_fields, ensure_truck_fuel_uom_uses_erpnext_uom


class TestOwnedTruckMaster(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("owned_truck_master_test")
		ensure_owned_truck_fields()
		self.demo = setup_demo_data()
		self.job = frappe.get_doc("Transport Job", self.demo["transport_job"])
		frappe.db.delete("Transport Trip", {"transport_job": self.job.name})

	def tearDown(self):
		frappe.db.rollback(save_point="owned_truck_master_test")

	def make_trip(self, **values):
		self.prepare_compatible_trip_fixture()
		doc = frappe.new_doc("Transport Trip")
		doc.update({
			"transport_job": self.job.name,
			"execution_source": "OWN",
			"trip_date": self.job.requested_date,
			"vehicle": self.demo["vehicle"],
			"driver": self.demo["driver"],
			"loading_site": self.job.loading_site,
			"unloading_site": self.job.unloading_site,
			"material": self.job.material,
			"planned_quantity": 1,
			"uom": self.job.uom,
		})
		doc.update(values)
		return doc

	def prepare_compatible_trip_fixture(self):
		frappe.db.set_value("Truck", self.demo["vehicle"], "vehicle_type", "TIPPER")
		frappe.db.set_value("Transport Job", self.job.name, "material", "3/4 AGREEGAT(10MM-20MM)")
		self.job.reload()

	def make_truck(self, **values):
		fuel_uom = self.demo["fuel_uom"]
		doc = frappe.new_doc("Truck")
		hash_value = frappe.generate_hash(length=8)
		doc.update({
			"truck_number": "TMS-OWN-" + hash_value,
			"license_plate": "TMS-OWN-" + hash_value,
			"make": "Test Make",
			"model": "Test Model",
			"manufacturing_year": "2026",
			"acquisition_date": 2026,
			"fuel_type": "Diesel",
			"fuel_uom": fuel_uom,
			"chassis_number": "CHS-" + hash_value,
			"status": "Idle",
			"disabled": 0,
			"ownership_type": "OWN",
		})
		doc.update(values)
		doc.insert()
		return doc

	def test_truck_field_installer_is_idempotent(self):
		before = frappe.db.count("Custom Field", {"dt": "Truck"})
		ensure_owned_truck_fields()
		ensure_owned_truck_fields()
		after = frappe.db.count("Custom Field", {"dt": "Truck"})
		self.assertEqual(before, after)

	def test_custom_truck_fields_exist(self):
		meta = frappe.get_meta("Truck")
		self.assertEqual(meta.get_field("fuel_uom").fieldtype, "Link")
		self.assertEqual(meta.get_field("fuel_uom").options, "UOM")
		self.assertEqual(meta.get_field("vehicle_type").options, "Truck Type")
		self.assertEqual(meta.get_field("capacity").fieldtype, "Float")
		self.assertEqual(meta.get_field("capacity_uom").options, "UOM")
		self.assertEqual(meta.get_field("ownership_type").options, "OWN")
		self.assertEqual(meta.get_field("ownership_type").default, "OWN")
		self.assertEqual(meta.get_field("registration_attachment").fieldtype, "Attach")
		self.assertEqual(meta.get_field("registration_attachment").label, "Registration Document")
		self.assertEqual(meta.get_field("insurance_attachment").fieldtype, "Attach")
		self.assertEqual(meta.get_field("insurance_attachment").label, "Insurance Document")
		self.assertEqual(meta.get_field("other_document_attachment").fieldtype, "Attach")
		self.assertEqual(meta.get_field("other_document_attachment").label, "Other Document")
		self.assertEqual(meta.get_field("erpnext_asset").options, "Asset")

	def test_fuel_uom_dependency_uses_erpnext_uom(self):
		field = frappe.get_meta("Truck").get_field("fuel_uom")
		self.assertEqual(field.fieldname, "fuel_uom")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "UOM")
		self.assertTrue(frappe.db.exists("UOM", "Litre"))
		self.assertEqual(frappe.db.get_value("Truck", self.demo["vehicle"], "fuel_uom"), "Litre")

	def test_fuel_uom_property_setter_is_idempotent(self):
		before = frappe.db.count(
			"Property Setter",
			{"doc_type": "Truck", "field_name": "fuel_uom", "property": "options"},
		)
		ensure_truck_fuel_uom_uses_erpnext_uom()
		ensure_truck_fuel_uom_uses_erpnext_uom()
		after = frappe.db.count(
			"Property Setter",
			{"doc_type": "Truck", "field_name": "fuel_uom", "property": "options"},
		)
		self.assertEqual(after, before)
		self.assertEqual(frappe.get_meta("Truck").get_field("fuel_uom").options, "UOM")

	def test_existing_truck_with_erpnext_fuel_uom_loads_and_saves(self):
		truck = frappe.get_doc("Truck", self.demo["vehicle"])
		self.assertEqual(truck.fuel_uom, "Litre")
		truck.save()
		self.assertEqual(frappe.db.get_value("Truck", truck.name, "fuel_uom"), "Litre")

	def test_existing_truck_loads_without_tms_trailer_dependency(self):
		truck = frappe.get_doc("Truck", "29413-FUJ")
		self.assertFalse(truck.get("trans_ms_default_trailer"))
		truck.save()
		self.assertFalse(frappe.db.get_value("Truck", truck.name, "trans_ms_default_trailer"))

	def test_no_live_legacy_vehicle_document_rows_exist(self):
		self.assertFalse(frappe.db.exists("DocType", "Document Attachments"))

	def test_existing_truck_attach_fields_save_and_reload(self):
		truck = frappe.get_doc("Truck", self.demo["vehicle"])
		truck.registration_attachment = "/files/tms-registration-test.txt"
		truck.insurance_attachment = "/files/tms-insurance-test.txt"
		truck.other_document_attachment = "/files/tms-other-document-test.txt"
		truck.save()

		reloaded = frappe.get_doc("Truck", truck.name)
		self.assertEqual(reloaded.registration_attachment, "/files/tms-registration-test.txt")
		self.assertEqual(reloaded.insurance_attachment, "/files/tms-insurance-test.txt")
		self.assertEqual(reloaded.other_document_attachment, "/files/tms-other-document-test.txt")

		reloaded.registration_attachment = None
		reloaded.insurance_attachment = None
		reloaded.other_document_attachment = None
		reloaded.save()

	def test_demo_does_not_create_fleet_fuel_uom(self):
		self.assertFalse(frappe.db.exists("DocType", "Fuel UOM"))
		ensure_owned_truck_fields()
		self.assertFalse(frappe.db.exists("DocType", "Fuel UOM"))

	def test_active_transport_management_code_no_longer_depends_on_fuel_uom_master(self):
		app_root = Path(__file__).resolve().parents[1]
		active_files = [
			app_root / "demo.py",
			app_root / "truck_master.py",
		]
		for path in active_files:
			self.assertNotIn('"Fuel UOM"', path.read_text())

	def test_active_transport_management_code_no_longer_depends_on_fleet_document_tables(self):
		app_root = Path(__file__).resolve().parents[1]
		active_files = [
			app_root / "demo.py",
			app_root / "truck_driver_master.py",
			app_root / "transport_management" / "doctype" / "truck" / "truck.py",
			app_root / "transport_management" / "doctype" / "transport_trip" / "transport_trip.py",
		]
		for path in active_files:
			source = path.read_text()
			self.assertNotIn("Document Attachments", source)
			self.assertNotIn("Document Name", source)
			self.assertNotIn("vehicle_documents", source)

	def test_existing_truck_defaults_to_owned(self):
		frappe.db.set_value("Truck", self.demo["vehicle"], "ownership_type", None)
		ensure_owned_truck_fields()
		self.assertEqual(frappe.db.get_value("Truck", self.demo["vehicle"], "ownership_type"), "OWN")

	def test_create_active_owned_truck(self):
		truck = self.make_truck(capacity=30, capacity_uom=self.demo["uom"])
		self.assertEqual(truck.ownership_type, "OWN")
		self.assertEqual(truck.status, "Idle")
		self.assertFalse(truck.disabled)

	def test_valid_enabled_idle_truck_accepted_for_own_trip(self):
		trip = self.make_trip()
		trip.insert()
		self.assertEqual(trip.vehicle, self.demo["vehicle"])

	def test_disabled_truck_rejected_for_own_trip(self):
		frappe.db.set_value("Truck", self.demo["vehicle"], "disabled", 1)
		with self.assertRaises(frappe.ValidationError):
			self.make_trip().insert()

	def test_non_idle_truck_rejected_for_own_trip(self):
		for status in ("Under Maintenance", "On Trip", "Disabled"):
			with self.subTest(status=status):
				frappe.db.set_value("Truck", self.demo["vehicle"], {"status": status, "disabled": 0})
				with self.assertRaises(frappe.ValidationError):
					self.make_trip().insert()
				frappe.db.set_value("Truck", self.demo["vehicle"], "status", "Idle")

	def test_trip_driver_can_differ_from_truck_default_driver(self):
		frappe.db.set_value("Truck", self.demo["vehicle"], "trans_ms_driver", None)
		trip = self.make_trip()
		trip.insert()
		self.assertEqual(trip.driver, self.demo["driver"])

	def test_optional_asset_link_field_targets_erpnext_asset(self):
		field = frappe.get_meta("Truck").get_field("erpnext_asset")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Asset")
