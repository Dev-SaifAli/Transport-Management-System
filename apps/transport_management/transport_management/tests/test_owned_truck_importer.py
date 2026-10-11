"""Tests for Owned Truck import preview and import behavior."""

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

import frappe
from frappe.utils.file_manager import save_file
from openpyxl import Workbook

from transport_management.imports import base_importer
from transport_management.imports.owned_truck_importer import (
	dry_run_owned_truck_import,
	import_new_owned_trucks,
	normalize_plate,
	normalize_truck_type,
)
from transport_management.truck_type_master import LEGACY_BULKER_TYPE, normalize_operational_truck_types


class TestOwnedTruckImport(unittest.TestCase):
	def make_workbook(self, rows):
		workbook = Workbook()
		sheet = workbook.active
		for row in rows:
			sheet.append(row)
		tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
		tmp.close()
		path = Path(tmp.name)
		workbook.save(path)
		workbook.close()
		self.addCleanup(path.unlink, missing_ok=True)
		return path

	def make_file_doc(self, rows):
		workbook = Workbook()
		sheet = workbook.active
		for row in rows:
			sheet.append(row)
		buffer = BytesIO()
		workbook.save(buffer)
		workbook.close()
		file_doc = save_file(
			f"tms_owned_truck_test_{frappe.generate_hash(length=8)}.xlsx",
			buffer.getvalue(),
			None,
			None,
			is_private=1,
		)
		frappe.db.commit()
		self.addCleanup(frappe.delete_doc_if_exists, "File", file_doc.name, force=1)
		return file_doc

	def cleanup_truck(self, truck):
		if frappe.db.exists("Truck", truck):
			frappe.delete_doc("Truck", truck, force=1)
			frappe.db.commit()

	def make_truck(self, plate, **values):
		self.cleanup_truck(plate)
		if not frappe.db.exists("Truck Type", values.get("vehicle_type") or "TIPPER"):
			truck_type = frappe.new_doc("Truck Type")
			truck_type.truck_type = values.get("vehicle_type") or "TIPPER"
			truck_type.insert()
			frappe.db.commit()

		doc = frappe.new_doc("Truck")
		doc.truck_number = plate
		doc.license_plate = plate
		doc.vehicle_type = values.pop("vehicle_type", "TIPPER")
		doc.ownership_type = values.pop("ownership_type", "OWN")
		doc.status = values.pop("status", "Idle")
		doc.disabled = values.pop("disabled", 0)
		doc.update(values)
		doc.insert()
		frappe.db.commit()
		self.addCleanup(self.cleanup_truck, plate)
		return doc

	def records_by_plate(self, result):
		return {row["normalized_plate"]: row for row in result["records"] if row.get("normalized_plate")}

	def test_plate_normalization(self):
		self.assertEqual(normalize_plate("29413 FUJ"), "29413-FUJ")
		self.assertEqual(normalize_plate("29413-FUJ"), "29413-FUJ")
		self.assertEqual(normalize_plate("29413 - FUJ"), "29413-FUJ")
		self.assertEqual(normalize_plate("29413-fuj"), "29413-FUJ")
		self.assertEqual(normalize_plate("22884 DXB"), "22884-DXB")
		self.assertEqual(normalize_plate("71922 RAK"), "71922-RAK")

	def test_bulker_source_normalizes_to_tanker(self):
		self.assertEqual(normalize_truck_type("BULKER"), "TANKER")
		self.assertEqual(normalize_truck_type("bulker"), "TANKER")
		self.assertEqual(normalize_truck_type(" TANKER "), "TANKER")

	def test_malformed_and_unsupported_plate_is_invalid(self):
		path = self.make_workbook([["License Plate", "Truck Type"], ["BAD", "TIPPER"], ["12345 AUH", "TIPPER"]])
		result = dry_run_owned_truck_import(path)
		self.assertEqual(result["summary"]["invalid"], 2)

	def test_duplicate_source_plate_detected_after_normalization(self):
		path = self.make_workbook([["License Plate", "Truck Type"], ["29413 FUJ", "TIPPER"], ["29413-FUJ", "TIPPER"]])
		result = dry_run_owned_truck_import(path)
		self.assertEqual(result["records"][0]["status"], "EXISTS")
		self.assertEqual(result["records"][1]["status"], "DUPLICATE_SOURCE")

	def test_existing_29413_source_is_exists(self):
		path = self.make_workbook([["License Plate", "Truck Type"], ["29413 FUJ", "TIPPER"]])
		result = dry_run_owned_truck_import(path)
		self.assertEqual(self.records_by_plate(result)["29413-FUJ"]["status"], "EXISTS")

	def test_new_owned_truck_preview(self):
		self.cleanup_truck("99111-DXB")
		path = self.make_workbook([["License Plate", "Truck Type"], ["99111 DXB", "TIPPER"]])
		result = dry_run_owned_truck_import(path)
		row = self.records_by_plate(result)["99111-DXB"]
		self.assertEqual(row["status"], "NEW")
		self.assertEqual(row["source_truck_type"], "TIPPER")

	def test_existing_different_vehicle_type_is_update_type(self):
		self.make_truck("99112-DXB", vehicle_type="TIPPER")
		path = self.make_workbook([["License Plate", "Truck Type"], ["99112 DXB", "TANKER"]])
		result = dry_run_owned_truck_import(path)
		self.assertEqual(self.records_by_plate(result)["99112-DXB"]["status"], "UPDATE_TYPE")

	def test_existing_tanker_and_source_bulker_compare_as_exists(self):
		self.make_truck("99120-DXB", vehicle_type="TANKER")
		path = self.make_workbook([["License Plate", "Truck Type"], ["99120 DXB", "BULKER"]])
		result = dry_run_owned_truck_import(path)
		row = self.records_by_plate(result)["99120-DXB"]
		self.assertEqual(row["status"], "EXISTS")
		self.assertEqual(row["source_truck_type"], "TANKER")

	def test_existing_non_own_plate_is_ownership_conflict(self):
		self.make_truck("99113-DXB", ownership_type="OWN")
		frappe.db.set_value("Truck", "99113-DXB", "ownership_type", "HIRED")
		frappe.db.commit()
		path = self.make_workbook([["License Plate", "Truck Type"], ["99113 DXB", "TIPPER"]])
		result = dry_run_owned_truck_import(path)
		self.assertEqual(self.records_by_plate(result)["99113-DXB"]["status"], "OWNERSHIP_CONFLICT")

	def test_dry_run_performs_zero_truck_and_type_writes(self):
		before_trucks = frappe.db.count("Truck")
		before_types = frappe.db.count("Truck Type")
		path = self.make_workbook([["License Plate", "Truck Type"], ["99114 DXB", "TIPPER"]])
		dry_run_owned_truck_import(path)
		self.assertEqual(frappe.db.count("Truck"), before_trucks)
		self.assertEqual(frappe.db.count("Truck Type"), before_types)

	def test_import_creates_new_only_and_leaves_unverified_fields_blank(self):
		self.cleanup_truck("99115-DXB")
		path = self.make_workbook([["License Plate", "Truck Type"], ["99115 DXB", "BULKER"], ["29413 FUJ", "TIPPER"]])
		result = import_new_owned_trucks(path)
		self.addCleanup(self.cleanup_truck, "99115-DXB")
		self.assertEqual(result["summary"]["created"], 1)
		self.assertEqual(result["summary"]["skipped"], 1)

		truck = frappe.get_doc("Truck", "99115-DXB")
		self.assertEqual(truck.truck_number, "99115-DXB")
		self.assertEqual(truck.license_plate, "99115-DXB")
		self.assertEqual(truck.vehicle_type, "TANKER")
		self.assertEqual(truck.ownership_type, "OWN")
		self.assertEqual(truck.status, "Idle")
		self.assertEqual(truck.disabled, 0)
		for fieldname in (
			"make",
			"model",
			"manufacturing_year",
			"capacity",
			"capacity_uom",
			"registration_expiry",
			"insurance_policy_number",
			"insurance_expiry",
			"erpnext_asset",
			"trans_ms_driver",
			"odometer_value",
			"engine_number",
			"chassis_number",
		):
			self.assertFalse(truck.get(fieldname))

	def test_second_import_creates_zero_trucks(self):
		self.cleanup_truck("99116-RAK")
		path = self.make_workbook([["License Plate", "Truck Type"], ["99116 RAK", "TIPPER"]])
		first = import_new_owned_trucks(path)
		second = import_new_owned_trucks(path)
		self.addCleanup(self.cleanup_truck, "99116-RAK")
		self.assertEqual(first["summary"]["created"], 1)
		self.assertEqual(second["summary"]["created"], 0)
		self.assertEqual(self.records_by_plate(second)["99116-RAK"]["status"], "EXISTS")

	def test_truck_type_created_during_import_if_missing(self):
		self.cleanup_truck("99117-FUJ")
		path = self.make_workbook([["License Plate", "Truck Type"], ["99117 FUJ", "TIPPER"]])
		result = import_new_owned_trucks(path)
		self.addCleanup(self.cleanup_truck, "99117-FUJ")
		self.assertEqual(result["summary"]["created"], 1)
		self.assertTrue(frappe.db.exists("Truck Type", "TIPPER"))

	def test_bulker_source_does_not_create_bulker_truck_type(self):
		self.cleanup_truck("99121-RAK")
		if frappe.db.exists("Truck Type", LEGACY_BULKER_TYPE):
			frappe.delete_doc("Truck Type", LEGACY_BULKER_TYPE, force=1)
			frappe.db.commit()
		path = self.make_workbook([["License Plate", "Truck Type"], ["99121 RAK", "BULKER"]])
		result = import_new_owned_trucks(path)
		self.addCleanup(self.cleanup_truck, "99121-RAK")
		self.assertEqual(result["summary"]["created"], 1)
		self.assertEqual(frappe.db.get_value("Truck", "99121-RAK", "vehicle_type"), "TANKER")
		self.assertFalse(frappe.db.exists("Truck Type", LEGACY_BULKER_TYPE))
		self.assertTrue(frappe.db.exists("Truck Type", "TANKER"))

	def test_live_bulker_links_are_migrated_to_tanker(self):
		self.make_truck("99122-FUJ", vehicle_type="TANKER")
		frappe.db.set_value("Truck", "99122-FUJ", "vehicle_type", LEGACY_BULKER_TYPE)
		frappe.db.commit()
		normalize_operational_truck_types()
		self.assertEqual(frappe.db.get_value("Truck", "99122-FUJ", "vehicle_type"), "TANKER")
		self.assertEqual(frappe.db.count("Truck", {"vehicle_type": LEGACY_BULKER_TYPE}), 0)
		self.assertEqual(frappe.db.count("Hired Vehicle", {"vehicle_type": LEGACY_BULKER_TYPE}), 0)

	def test_import_api_creates_log(self):
		self.cleanup_truck("99118-DXB")
		file_doc = self.make_file_doc([["License Plate", "Truck Type"], ["99118 DXB", "BULKER"]])
		before = frappe.db.count("TMS Import Log")
		result = base_importer.run_import("Owned Trucks", file_doc.name)
		self.addCleanup(self.cleanup_truck, "99118-DXB")
		self.assertEqual(result["summary"]["created"], 1)
		self.assertEqual(frappe.db.count("TMS Import Log"), before + 1)
		log = frappe.get_last_doc("TMS Import Log")
		self.addCleanup(frappe.delete_doc_if_exists, "TMS Import Log", log.name, force=1)
		self.assertEqual(log.import_type, "Owned Trucks")
		self.assertEqual(log.created_count, 1)

	def test_api_permission_protection(self):
		file_doc = self.make_file_doc([["License Plate", "Truck Type"], ["99119 DXB", "TIPPER"]])
		current_user = frappe.session.user
		try:
			frappe.set_user("Guest")
			with self.assertRaises(frappe.PermissionError):
				base_importer.dry_run_import("Owned Trucks", file_doc.name)
		finally:
			frappe.set_user(current_user)

	def test_location_importer_still_dispatches(self):
		file_doc = self.make_file_doc([["LOCATION LOAD - LOCATION UNLOAD"]])
		result = base_importer.dry_run_import("Transport Locations", file_doc.name)
		self.assertEqual(result["summary"]["new"], 2)
