"""Tests for Materials import and allowed Truck Type compatibility."""

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

import frappe
from frappe.utils.file_manager import save_file
from openpyxl import Workbook

from transport_management.cargo_type_master import get_allowed_truck_types
from transport_management.imports import base_importer
from transport_management.imports.material_importer import (
	dry_run_material_import,
	import_new_materials,
	normalize_active,
	normalize_material_name,
)


class TestMaterialImport(unittest.TestCase):
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
			f"tms_material_test_{frappe.generate_hash(length=8)}.xlsx",
			buffer.getvalue(),
			None,
			None,
			is_private=1,
		)
		frappe.db.commit()
		self.addCleanup(frappe.delete_doc_if_exists, "File", file_doc.name, force=1)
		return file_doc

	def cleanup_material(self, material):
		if frappe.db.exists("Cargo Types", material):
			frappe.delete_doc("Cargo Types", material, force=1)
			frappe.db.commit()

	def make_material(self, material, truck_types=()):
		self.cleanup_material(material)
		doc = frappe.new_doc("Cargo Types")
		doc.cargo_name = material
		doc.active = 1
		for truck_type in truck_types:
			doc.append("allowed_truck_types", {"truck_type": truck_type})
		doc.insert()
		frappe.db.commit()
		self.addCleanup(self.cleanup_material, material)
		return doc

	def records_by_pair(self, result):
		return {(row["material_name"], row["truck_type"]): row for row in result["records"]}

	def test_material_name_whitespace_normalization(self):
		self.assertEqual(normalize_material_name("  CEMENT  "), "CEMENT")
		self.assertEqual(normalize_material_name("3/16   BLACK   SAND"), "3/16 BLACK SAND")

	def test_active_normalization(self):
		self.assertEqual(normalize_active("1"), 1)
		self.assertEqual(normalize_active("yes"), 1)
		self.assertEqual(normalize_active("0"), 0)
		self.assertEqual(normalize_active("inactive"), 0)

	def test_tipper_tanker_and_bulker_alias_are_accepted(self):
		path = self.make_workbook([
			["Material Name", "Allowed Truck Type", "Active"],
			["TMS MAT TIPPER", "TIPPER", 1],
			["TMS MAT TANKER", "TANKER", 1],
			["TMS MAT BULKER", "BULKER", 1],
		])
		result = dry_run_material_import(path)
		self.assertEqual(result["summary"]["invalid"], 0)
		self.assertEqual(self.records_by_pair(result)[("TMS MAT BULKER", "TANKER")]["status"], "NEW")

	def test_case_insensitive_duplicate_material_pair_detected(self):
		path = self.make_workbook([
			["Material Name", "Allowed Truck Type"],
			["TMS DUP MAT", "TIPPER"],
			[" tms   dup   mat ", "TIPPER"],
		])
		result = dry_run_material_import(path)
		self.assertEqual(result["summary"]["duplicate_source"], 1)

	def test_same_material_with_two_truck_types_aggregates_on_import(self):
		material = "TMS MULTI MATERIAL " + frappe.generate_hash(length=6)
		path = self.make_workbook([
			["Material Name", "Allowed Truck Type"],
			[material, "TIPPER"],
			[material, "TANKER"],
		])
		result = import_new_materials(path)
		self.addCleanup(self.cleanup_material, material)
		self.assertEqual(result["summary"]["created"], 1)
		self.assertEqual(result["summary"]["created_compatibility_rows"], 2)
		self.assertEqual(sorted(get_allowed_truck_types(material)), ["TANKER", "TIPPER"])

	def test_existing_compatible_material_is_exists(self):
		material = "TMS EXISTING MATERIAL " + frappe.generate_hash(length=6)
		self.make_material(material, ("TIPPER",))
		path = self.make_workbook([["Material Name", "Allowed Truck Type"], [material, "TIPPER"]])
		result = dry_run_material_import(path)
		self.assertEqual(self.records_by_pair(result)[(material, "TIPPER")]["status"], "EXISTS")

	def test_existing_material_new_truck_type_is_update_compatibility(self):
		material = "TMS UPDATE MATERIAL " + frappe.generate_hash(length=6)
		self.make_material(material, ("TIPPER",))
		path = self.make_workbook([["Material Name", "Allowed Truck Type"], [material, "TANKER"]])
		result = dry_run_material_import(path)
		self.assertEqual(self.records_by_pair(result)[(material, "TANKER")]["status"], "UPDATE_COMPATIBILITY")

	def test_dry_run_performs_zero_writes(self):
		before_materials = frappe.db.count("Cargo Types")
		before_rows = frappe.db.count("Material Allowed Truck Type")
		path = self.make_workbook([["Material Name", "Allowed Truck Type"], ["TMS DRY RUN MATERIAL", "TIPPER"]])
		dry_run_material_import(path)
		self.assertEqual(frappe.db.count("Cargo Types"), before_materials)
		self.assertEqual(frappe.db.count("Material Allowed Truck Type"), before_rows)

	def test_actual_import_creates_new_material_and_child_rows(self):
		material = "TMS NEW MATERIAL " + frappe.generate_hash(length=6)
		path = self.make_workbook([["Material Name", "Allowed Truck Type", "Active"], [material, "BULKER", "1"]])
		result = import_new_materials(path)
		self.addCleanup(self.cleanup_material, material)
		self.assertEqual(result["summary"]["created"], 1)
		self.assertEqual(result["summary"]["created_compatibility_rows"], 1)
		self.assertEqual(get_allowed_truck_types(material), ["TANKER"])
		self.assertFalse(frappe.db.exists("Truck Type", "BULKER"))

	def test_second_import_is_idempotent(self):
		material = "TMS IDEMPOTENT MATERIAL " + frappe.generate_hash(length=6)
		path = self.make_workbook([["Material Name", "Allowed Truck Type"], [material, "TIPPER"]])
		first = import_new_materials(path)
		second = import_new_materials(path)
		self.addCleanup(self.cleanup_material, material)
		self.assertEqual(first["summary"]["created"], 1)
		self.assertEqual(second["summary"]["created"], 0)
		self.assertEqual(second["summary"]["exists"], 1)

	def test_invalid_rows(self):
		path = self.make_workbook([
			["Material Name", "Allowed Truck Type", "Active"],
			["", "TIPPER", 1],
			["TMS BAD TYPE", "REEFER", 1],
			["TMS BAD ACTIVE", "TIPPER", "maybe"],
		])
		result = dry_run_material_import(path)
		self.assertEqual(result["summary"]["invalid"], 3)

	def test_material_import_api_creates_log(self):
		material = "TMS API MATERIAL " + frappe.generate_hash(length=6)
		file_doc = self.make_file_doc([["Material Name", "Allowed Truck Type"], [material, "TIPPER"]])
		before = frappe.db.count("TMS Import Log")
		result = base_importer.run_import("Materials", file_doc.name)
		self.addCleanup(self.cleanup_material, material)
		self.assertEqual(result["summary"]["created"], 1)
		self.assertEqual(frappe.db.count("TMS Import Log"), before + 1)
		log = frappe.get_last_doc("TMS Import Log")
		self.addCleanup(frappe.delete_doc_if_exists, "TMS Import Log", log.name, force=1)
		self.assertEqual(log.import_type, "Materials")
		self.assertEqual(log.created_count, 1)

	def test_no_direct_truck_links_stored_in_material(self):
		meta = frappe.get_meta("Cargo Types")
		for field in meta.fields:
			self.assertFalse(field.fieldtype == "Link" and field.options == "Truck", field.fieldname)
			self.assertFalse(field.fieldtype == "Table" and field.options == "Truck", field.fieldname)

	def test_existing_cargo_types_data_is_preserved(self):
		self.assertTrue(frappe.db.exists("Cargo Types", "3/4 Aggregate"))

	def test_importer_regressions_still_dispatch(self):
		location_file = self.make_file_doc([["LOCATION LOAD - LOCATION UNLOAD"]])
		location_result = base_importer.dry_run_import("Transport Locations", location_file.name)
		self.assertEqual(location_result["summary"]["new"], 2)

		truck_file = self.make_file_doc([["License Plate", "Truck Type"], ["99130 DXB", "TIPPER"]])
		truck_result = base_importer.dry_run_import("Owned Trucks", truck_file.name)
		self.assertEqual(truck_result["summary"]["new"], 1)
