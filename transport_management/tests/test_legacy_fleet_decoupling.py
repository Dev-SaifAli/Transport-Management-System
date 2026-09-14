import json
import unittest
from pathlib import Path

import frappe


APP_ROOT = Path(frappe.get_app_path("transport_management")).parent


class TestLegacyFleetDecoupling(unittest.TestCase):
	def test_after_migrate_no_longer_installs_transportation_order_compatibility(self):
		setup_source = (APP_ROOT / "transport_management" / "setup.py").read_text()
		self.assertNotIn("ensure_assignment_table", setup_source)
		self.assertNotIn("ensure_transportation_order_ui", setup_source)
		self.assertNotIn("fleet_compatibility", setup_source)
		self.assertNotIn("transport_order_ui", setup_source)

	def test_transportation_order_client_hook_is_not_registered(self):
		hooks_source = (APP_ROOT / "transport_management" / "hooks.py").read_text()
		self.assertNotIn("Transportation Order", hooks_source)
		self.assertNotIn("transportation_order.js", hooks_source)
		self.assertFalse((APP_ROOT / "transport_management" / "public" / "js" / "transportation_order.js").exists())

	def test_active_job_and_trip_do_not_link_to_legacy_fleet_workflow(self):
		legacy_targets = {"Transportation Order", "Trips", "Manifest", "Trip Routes"}
		for doctype in ("Transport Job", "Transport Trip", "Hired Vehicle", "Transport Shipment"):
			meta = frappe.get_meta(doctype)
			actual_targets = {field.options for field in meta.fields if field.fieldtype in {"Link", "Table"} and field.options}
			self.assertFalse(actual_targets & legacy_targets, f"{doctype} links to {actual_targets & legacy_targets}")

	def test_fleet_master_dependencies_remain_available(self):
		for doctype in ("Truck", "Truck Driver", "Transport Location", "Cargo Types", "Truck Type"):
			self.assertTrue(frappe.db.exists("DocType", doctype), doctype)

	def test_vsd_fleet_legacy_doctypes_are_removed_after_uninstall(self):
		for doctype in ("Trailers", "Fuel UOM", "Document Attachments", "Trips", "Transportation Order"):
			self.assertFalse(frappe.db.exists("DocType", doctype), doctype)

	def test_transport_management_workspace_excludes_legacy_fleet_workflow(self):
		workspace = json.loads((APP_ROOT / "transport_management" / "transport_management" / "workspace" / "transport_management" / "transport_management.json").read_text())
		sidebar = json.loads((APP_ROOT / "transport_management" / "workspace_sidebar" / "transport_management.json").read_text())
		legacy = {"Transportation Order", "Transport Shipment", "Trips", "Manifest", "Trip Routes", "Trip Locations", "Fuel Requests", "Requested Payment", "Trailers"}
		workspace_targets = {row.get("label") for row in workspace["links"]} | {row.get("link_to") for row in workspace["links"]}
		sidebar_targets = {row.get("label") for row in sidebar["items"]} | {row.get("link_to") for row in sidebar["items"]}
		self.assertFalse(workspace_targets & legacy)
		self.assertFalse(sidebar_targets & legacy)

	def test_active_tms_doctypes_do_not_depend_on_trailers(self):
		for doctype in ("Transport Job", "Transport Trip", "Hired Vehicle"):
			meta = frappe.get_meta(doctype)
			targets = {
				field.options
				for field in meta.fields
				if field.fieldtype in {"Link", "Table"} and field.options
			}
			fieldnames = {field.fieldname for field in meta.fields}
			self.assertNotIn("Trailers", targets)
			self.assertFalse(any("trailer" in fieldname for fieldname in fieldnames))

	def test_active_tms_doctypes_do_not_depend_on_fleet_document_child_tables(self):
		for doctype in ("Truck Driver", "Transport Job", "Transport Trip", "Hired Vehicle"):
			meta = frappe.get_meta(doctype)
			targets = {
				field.options
				for field in meta.fields
				if field.fieldtype in {"Link", "Table"} and field.options
			}
			self.assertNotIn("Document Attachments", targets)
			self.assertNotIn("Document Name", targets)

	def test_active_transport_management_code_does_not_depend_on_trailers(self):
		active_files = [
			APP_ROOT / "transport_management" / "demo.py",
			APP_ROOT / "transport_management" / "truck_driver_master.py",
			APP_ROOT / "transport_management" / "transport_management" / "doctype" / "truck" / "truck.py",
			APP_ROOT / "transport_management" / "transport_management" / "doctype" / "transport_job" / "transport_job.py",
			APP_ROOT / "transport_management" / "transport_management" / "doctype" / "transport_trip" / "transport_trip.py",
			APP_ROOT / "transport_management" / "transport_management" / "doctype" / "hired_vehicle" / "hired_vehicle.py",
		]
		for path in active_files:
			source = path.read_text()
			self.assertNotIn("Trailers", source)
			self.assertNotIn("trans_ms_default_trailer", source)

	def test_demo_uses_current_job_trip_flow(self):
		from transport_management.demo import setup_demo_data

		frappe.db.savepoint("legacy_decoupling_demo_test")
		try:
			before_shipments = frappe.db.count("Transport Shipment")
			demo = setup_demo_data()
			self.assertTrue(demo["transport_job"])
			self.assertEqual(len(demo["transport_trips"]), 3)
			self.assertEqual(frappe.db.count("Transport Shipment"), before_shipments)
		finally:
			frappe.db.rollback(save_point="legacy_decoupling_demo_test")

	def test_transport_management_has_no_stale_transportation_order_customizations(self):
		self.assertEqual(frappe.db.count("Custom Field", {"dt": "Transportation Order", "module": "Transport Management"}), 0)
		self.assertEqual(frappe.db.count("Property Setter", {"doc_type": "Transportation Order", "module": "Transport Management"}), 0)
