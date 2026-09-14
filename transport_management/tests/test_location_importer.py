"""Tests for Transport Location import dry-run logic."""

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

import frappe
from openpyxl import Workbook
from frappe.utils.file_manager import save_file

from transport_management.imports import base_importer
from transport_management.imports.location_importer import (
	dry_run_location_import,
	import_new_locations,
	normalize_location,
)


class TestLocationImportDryRun(unittest.TestCase):
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

	def make_csv(self, rows):
		tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
		for row in rows:
			tmp.write(",".join("" if value is None else str(value) for value in row) + "\n")
		tmp.close()
		path = Path(tmp.name)
		self.addCleanup(path.unlink, missing_ok=True)
		return path

	def make_file_doc(self, rows, *, filename=None):
		filename = filename or f"tms_import_test_{frappe.generate_hash(length=8)}.xlsx"
		workbook = Workbook()
		sheet = workbook.active
		for row in rows:
			sheet.append(row)
		buffer = BytesIO()
		workbook.save(buffer)
		workbook.close()
		file_doc = save_file(filename, buffer.getvalue(), None, None, is_private=1)
		frappe.db.commit()
		self.addCleanup(frappe.delete_doc_if_exists, "File", file_doc.name, force=1)
		return file_doc

	def cleanup_location(self, location):
		if frappe.db.exists("Transport Location", location):
			frappe.delete_doc("Transport Location", location, force=1)
			frappe.db.commit()

	def records_by_location(self, result):
		return {row["location"]: row for row in result["records"]}

	def test_loading_only_and_unloading_only_sites(self):
		path = self.make_workbook([["SOURCE A", "DEST A"]])
		result = dry_run_location_import(path)
		records = self.records_by_location(result)
		self.assertEqual(records["SOURCE A"]["location_usage"], "Loading")
		self.assertEqual(records["DEST A"]["location_usage"], "Unloading")

	def test_same_site_on_both_sides_becomes_both(self):
		path = self.make_workbook([["SITE A", "SITE B"], ["SITE C", "SITE A"]])
		result = dry_run_location_import(path)
		self.assertEqual(self.records_by_location(result)["SITE A"]["location_usage"], "Both")

	def test_duplicate_whitespace_and_case_insensitive_deduplication(self):
		path = self.make_workbook([["  Site   A  ", "Dest A"], ["site a", "Dest B"]])
		result = dry_run_location_import(path)
		self.assertEqual(result["summary"]["unique_locations"], 3)
		site = self.records_by_location(result)["Site A"]
		self.assertEqual(site["location_usage"], "Loading")
		self.assertEqual(site["source_values"], ["Site A", "site a"])

	def test_existing_matching_location_is_exists(self):
		path = self.make_workbook([["ATBT AL TAWEEN", "NEW DEST"]])
		result = dry_run_location_import(path)
		self.assertEqual(self.records_by_location(result)["ATBT AL TAWEEN"]["status"], "EXISTS")

	def test_existing_loading_source_proves_both_is_update_usage(self):
		path = self.make_workbook([["NEW SOURCE", "ATBT AL TAWEEN"]])
		result = dry_run_location_import(path)
		row = self.records_by_location(result)["ATBT AL TAWEEN"]
		self.assertEqual(row["location_usage"], "Unloading")
		self.assertEqual(row["existing_usage"], "Loading")
		self.assertEqual(row["status"], "UPDATE_USAGE")

	def test_header_blank_and_invalid_rows(self):
		path = self.make_workbook([["Row Labels"], [None], ["A - B - C"], ["A - B"]])
		result = dry_run_location_import(path)
		self.assertEqual(result["summary"]["valid_rows"], 1)
		self.assertEqual(result["summary"]["invalid"], 1)
		records = self.records_by_location(result)
		self.assertIn("A", records)
		self.assertIn("B", records)

	def test_similar_spellings_are_not_merged(self):
		path = self.make_workbook([["ORYX DIC", "A"], ["ORYX-DIC", "B"], ["ORYX D.I.C", "C"]])
		result = dry_run_location_import(path)
		records = self.records_by_location(result)
		self.assertIn("ORYX DIC", records)
		self.assertIn("ORYX-DIC", records)
		self.assertIn("ORYX D.I.C", records)

	def test_dry_run_performs_zero_transport_location_writes(self):
		before_count = frappe.db.count("Transport Location")
		before_modified = dict(frappe.get_all("Transport Location", fields=["name", "modified"], as_list=True))
		path = self.make_workbook([["DRY RUN SOURCE", "DRY RUN DEST"]])
		dry_run_location_import(path)
		after_modified = dict(frappe.get_all("Transport Location", fields=["name", "modified"], as_list=True))
		self.assertEqual(frappe.db.count("Transport Location"), before_count)
		self.assertEqual(after_modified, before_modified)

	def test_normalize_location_only_changes_whitespace(self):
		self.assertEqual(normalize_location(" ORYX   D.I.C "), "ORYX D.I.C")
		self.assertEqual(normalize_location("ORYX-DIC"), "ORYX-DIC")

	def test_csv_source_is_supported(self):
		path = self.make_csv([["CSV LOAD - CSV UNLOAD"]])
		result = dry_run_location_import(path)
		records = self.records_by_location(result)
		self.assertEqual(records["CSV LOAD"]["location_usage"], "Loading")
		self.assertEqual(records["CSV UNLOAD"]["location_usage"], "Unloading")

	def test_actual_import_creates_new_only_with_defaults_and_blanks(self):
		for location in ("IMPORT LOAD A", "IMPORT UNLOAD A"):
			self.cleanup_location(location)

		path = self.make_workbook([["IMPORT LOAD A - IMPORT UNLOAD A"], ["ATBT AL TAWEEN - IMPORT UNLOAD A"]])
		result = import_new_locations(path)
		self.addCleanup(self.cleanup_location, "IMPORT LOAD A")
		self.addCleanup(self.cleanup_location, "IMPORT UNLOAD A")

		self.assertEqual(result["summary"]["created"], 2)
		self.assertEqual(result["summary"]["skipped"], 1)
		self.assertEqual(result["summary"]["failed"], 0)
		self.assertEqual(frappe.db.get_value("Transport Location", "ATBT AL TAWEEN", "location_usage"), "Loading")

		created = frappe.get_doc("Transport Location", "IMPORT UNLOAD A")
		self.assertEqual(created.location, "IMPORT UNLOAD A")
		self.assertEqual(created.location_usage, "Unloading")
		self.assertEqual(created.location_type, "Other")
		self.assertEqual(created.country, "United Arab Emirates")
		self.assertEqual(created.active, 1)
		self.assertFalse(created.customer)
		self.assertFalse(created.supplier)
		self.assertFalse(created.address)
		self.assertFalse(created.city)
		self.assertFalse(created.latitude)
		self.assertFalse(created.longitude)
		self.assertFalse(created.notes)

	def test_second_import_is_idempotent(self):
		for location in ("IDEMPOTENT LOAD", "IDEMPOTENT UNLOAD"):
			self.cleanup_location(location)

		path = self.make_workbook([["IDEMPOTENT LOAD - IDEMPOTENT UNLOAD"]])
		first = import_new_locations(path)
		second = import_new_locations(path)
		self.addCleanup(self.cleanup_location, "IDEMPOTENT LOAD")
		self.addCleanup(self.cleanup_location, "IDEMPOTENT UNLOAD")

		self.assertEqual(first["summary"]["created"], 2)
		self.assertEqual(second["summary"]["created"], 0)
		self.assertEqual(second["summary"]["exists"], 2)

	def test_update_usage_is_not_automatically_changed(self):
		path = self.make_workbook([["NEW SOURCE", "ATBT AL TAWEEN"]])
		result = import_new_locations(path)
		self.addCleanup(self.cleanup_location, "NEW SOURCE")
		self.assertEqual(self.records_by_location(result)["ATBT AL TAWEEN"]["status"], "UPDATE_USAGE")
		self.assertEqual(frappe.db.get_value("Transport Location", "ATBT AL TAWEEN", "location_usage"), "Loading")

	def test_invalid_file_type_rejected(self):
		file_doc = save_file(f"tms_import_test_{frappe.generate_hash(length=8)}.txt", b"not an import file", None, None, is_private=1)
		frappe.db.commit()
		self.addCleanup(frappe.delete_doc_if_exists, "File", file_doc.name, force=1)
		with self.assertRaises(frappe.ValidationError):
			base_importer.dry_run_import("Transport Locations", file_doc.name)

	def test_import_api_is_restricted_to_system_manager(self):
		file_doc = self.make_file_doc([["API LOAD - API UNLOAD"]])
		current_user = frappe.session.user
		try:
			frappe.set_user("Guest")
			with self.assertRaises(frappe.PermissionError):
				base_importer.dry_run_import("Transport Locations", file_doc.name)
		finally:
			frappe.set_user(current_user)

	def test_import_api_creates_audit_log(self):
		for location in ("LOG LOAD", "LOG UNLOAD"):
			self.cleanup_location(location)

		file_doc = self.make_file_doc(
			[["LOG LOAD - LOG UNLOAD"]],
			filename=f"tms_import_log_test_{frappe.generate_hash(length=8)}.xlsx",
		)
		before = frappe.db.count("TMS Import Log")
		result = base_importer.run_import("Transport Locations", file_doc.name)
		self.addCleanup(self.cleanup_location, "LOG LOAD")
		self.addCleanup(self.cleanup_location, "LOG UNLOAD")

		self.assertEqual(result["summary"]["created"], 2)
		self.assertEqual(frappe.db.count("TMS Import Log"), before + 1)
		log = frappe.get_last_doc("TMS Import Log")
		self.addCleanup(frappe.delete_doc_if_exists, "TMS Import Log", log.name, force=1)
		self.assertEqual(log.import_type, "Transport Locations")
		self.assertEqual(log.source_file, file_doc.name)
		self.assertEqual(log.filename, file_doc.file_name)
		self.assertEqual(log.source_rows, 1)
		self.assertEqual(log.created_count, 2)

	def test_existing_job_and_trip_links_remain_untouched_after_import(self):
		before_jobs = frappe.get_all("Transport Job", fields=["name", "loading_site", "unloading_site"], as_list=True)
		before_trips = frappe.get_all("Transport Trip", fields=["name", "loading_site", "unloading_site"], as_list=True)
		path = self.make_workbook([["LINK SAFE LOAD - LINK SAFE UNLOAD"]])
		import_new_locations(path)
		self.addCleanup(self.cleanup_location, "LINK SAFE LOAD")
		self.addCleanup(self.cleanup_location, "LINK SAFE UNLOAD")

		after_jobs = frappe.get_all("Transport Job", fields=["name", "loading_site", "unloading_site"], as_list=True)
		after_trips = frappe.get_all("Transport Trip", fields=["name", "loading_site", "unloading_site"], as_list=True)
		self.assertEqual(after_jobs, before_jobs)
		self.assertEqual(after_trips, before_trips)
