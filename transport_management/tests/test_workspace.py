import json
import unittest
from pathlib import Path

import frappe


APP_ROOT = Path(frappe.get_app_path("transport_management")).parent
WORKSPACE_PATH = APP_ROOT / "transport_management" / "transport_management" / "workspace" / "transport_management" / "transport_management.json"
HIRED_VEHICLE_PATH = APP_ROOT / "transport_management" / "transport_management" / "doctype" / "hired_vehicle" / "hired_vehicle.json"


class TestTransportManagementWorkspace(unittest.TestCase):
	def load_workspace(self):
		return json.loads(WORKSPACE_PATH.read_text())

	def test_workspace_metadata_is_public_and_module_owned(self):
		workspace = self.load_workspace()
		self.assertEqual(workspace["doctype"], "Workspace")
		self.assertEqual(workspace["name"], "Transport Management")
		self.assertEqual(workspace["label"], "Transport Management")
		self.assertEqual(workspace["module"], "Transport Management")
		self.assertEqual(workspace["app"], "transport_management")
		self.assertEqual(workspace["public"], 1)
		self.assertFalse(workspace["is_hidden"])

	def test_workspace_links_expected_sections_without_legacy_fleet_flows(self):
		workspace = self.load_workspace()
		links = workspace["links"]
		sections = [row["label"] for row in links if row["type"] == "Card Break"]
		self.assertEqual(sections, ["Operations", "Fleet", "Masters", "ERP"])

		linked_doctypes = {row.get("link_to"): row.get("label") for row in links if row["type"] == "Link"}
		self.assertEqual(linked_doctypes["Transport Job"], "Transport Job")
		self.assertEqual(linked_doctypes["Transport Trip"], "Transport Trip")
		self.assertEqual(linked_doctypes["Truck"], "Owned Trucks")
		self.assertEqual(linked_doctypes["Hired Vehicle"], "Hired Vehicle")
		self.assertEqual(linked_doctypes["Truck Driver"], "Drivers")
		self.assertEqual(linked_doctypes["Trailers"], "Trailers")
		self.assertEqual(linked_doctypes["Supplier"], "Suppliers / Transporters")
		self.assertEqual(linked_doctypes["Cargo Types"], "Materials")

		for legacy in ("Transport Shipment", "Trips", "Manifest", "Trip Routes", "Trip Locations"):
			self.assertNotIn(legacy, linked_doctypes)

	def test_workspace_has_only_document_number_cards(self):
		workspace = self.load_workspace()
		cards = {row["number_card_name"] for row in workspace["number_cards"]}
		self.assertEqual(cards, {
			"Total Transport Jobs",
			"Active Transport Trips",
			"Trips In Transit",
			"Trips Awaiting POD",
			"Active Hired Vehicles",
		})
		self.assertFalse(any(row.get("link_type") == "Report" for row in workspace["links"]))

	def test_hired_vehicle_has_searchable_plate_metadata(self):
		metadata = json.loads(HIRED_VEHICLE_PATH.read_text())
		self.assertEqual(metadata["title_field"], "plate_number")
		self.assertEqual(metadata["search_fields"], "plate_number,transporter")
