import json
import unittest
from pathlib import Path

import frappe


APP_ROOT = Path(frappe.get_app_path("transport_management")).parent
WORKSPACE_PATH = APP_ROOT / "transport_management" / "transport_management" / "workspace" / "transport_management" / "transport_management.json"
HIRED_VEHICLE_PATH = APP_ROOT / "transport_management" / "transport_management" / "doctype" / "hired_vehicle" / "hired_vehicle.json"
PAGE_ROOT = APP_ROOT / "transport_management" / "transport_management" / "page"
SIDEBAR_PATH = APP_ROOT / "transport_management" / "workspace_sidebar" / "transport_management.json"
DESKTOP_ICON_PATH = APP_ROOT / "transport_management" / "desktop_icon" / "transport_management.json"

WRAPPER_PAGES = {
	"tms-customers": "Transport Management / Customers",
	"tms-suppliers": "Transport Management / Suppliers",
	"tms-owned-trucks": "Transport Management / Owned Trucks",
	"tms-drivers": "Transport Management / Drivers",
	"tms-locations": "Transport Management / Locations",
}

TMS_TOOL_PAGES = {
	"tms-data-import": "Transport Management / Data Import",
}


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

		linked_doctypes = {
			row.get("link_to"): row.get("label")
			for row in links
			if row["type"] == "Link" and row.get("link_type") == "DocType"
		}
		self.assertEqual(linked_doctypes["Transport Job"], "Transport Job")
		self.assertEqual(linked_doctypes["Transport Trip"], "Transport Trip")
		self.assertEqual(linked_doctypes["Hired Vehicle"], "Hired Vehicles")
		self.assertEqual(linked_doctypes["Cargo Types"], "Materials")

		linked_pages = {
			row.get("link_to"): row.get("label")
			for row in links
			if row["type"] == "Link" and row.get("link_type") == "Page"
		}
		self.assertEqual(linked_pages["tms-owned-trucks"], "Owned Trucks")
		self.assertEqual(linked_pages["tms-drivers"], "Drivers")
		self.assertEqual(linked_pages["tms-customers"], "Customers")
		self.assertEqual(linked_pages["tms-suppliers"], "Suppliers / Transporters")
		self.assertEqual(linked_pages["tms-locations"], "Transport Locations")
		self.assertEqual(linked_pages["tms-data-import"], "Data Import")

		all_links = {row.get("link_to") for row in links if row["type"] == "Link"}
		for legacy in ("Transport Shipment", "Trips", "Manifest", "Trip Routes", "Trip Locations", "Trailers"):
			self.assertNotIn(legacy, all_links)

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

	def test_tms_wrapper_pages_exist_and_belong_to_transport_management(self):
		for page_name, title in {**WRAPPER_PAGES, **TMS_TOOL_PAGES}.items():
			folder = page_name.replace("-", "_")
			metadata_path = PAGE_ROOT / folder / f"{folder}.json"
			self.assertTrue(metadata_path.exists(), page_name)
			metadata = json.loads(metadata_path.read_text())
			self.assertEqual(metadata["doctype"], "Page")
			self.assertEqual(metadata["name"], page_name)
			self.assertEqual(metadata["page_name"], page_name)
			self.assertEqual(metadata["title"], title)
			self.assertEqual(metadata["module"], "Transport Management")
			self.assertEqual(metadata["standard"], "Yes")

			script_path = metadata_path.with_suffix(".js")
			self.assertTrue(script_path.exists(), page_name)

	def test_tms_data_import_page_is_system_manager_only(self):
		metadata_path = PAGE_ROOT / "tms_data_import" / "tms_data_import.json"
		metadata = json.loads(metadata_path.read_text())
		self.assertEqual(metadata["name"], "tms-data-import")
		self.assertEqual(metadata["module"], "Transport Management")
		self.assertEqual(metadata["roles"], [{"role": "System Manager"}])

	def test_tms_owned_doctypes_remain_direct_workspace_links(self):
		workspace = self.load_workspace()
		direct_links = {
			row.get("link_to"): row.get("link_type")
			for row in workspace["links"]
			if row["type"] == "Link"
		}
		self.assertEqual(direct_links["Transport Job"], "DocType")
		self.assertEqual(direct_links["Transport Trip"], "DocType")
		self.assertEqual(direct_links["Hired Vehicle"], "DocType")

	def load_sidebar(self):
		return json.loads(SIDEBAR_PATH.read_text())

	def test_transport_management_workspace_sidebar_metadata(self):
		sidebar = self.load_sidebar()
		self.assertEqual(sidebar["doctype"], "Workspace Sidebar")
		self.assertEqual(sidebar["name"], "Transport Management")
		self.assertEqual(sidebar["title"], "Transport Management")
		self.assertEqual(sidebar["module"], "Transport Management")
		self.assertEqual(sidebar["app"], "transport_management")
		self.assertEqual(sidebar["standard"], 1)

	def test_transport_management_sidebar_links(self):
		items = self.load_sidebar()["items"]
		sections = [row["label"] for row in items if row["type"] == "Section Break"]
		self.assertEqual(sections, ["Operations", "Fleet", "Masters", "ERP"])

		links = {row["label"]: (row.get("link_type"), row.get("link_to")) for row in items if row["type"] == "Link"}
		self.assertEqual(links["Home"], ("Workspace", "Transport Management"))
		self.assertEqual(links["Transport Job"], ("DocType", "Transport Job"))
		self.assertEqual(links["Transport Trip"], ("DocType", "Transport Trip"))
		self.assertEqual(links["Owned Trucks"], ("Page", "tms-owned-trucks"))
		self.assertEqual(links["Hired Vehicles"], ("DocType", "Hired Vehicle"))
		self.assertEqual(links["Drivers"], ("Page", "tms-drivers"))
		self.assertEqual(links["Customers"], ("Page", "tms-customers"))
		self.assertEqual(links["Suppliers / Transporters"], ("Page", "tms-suppliers"))
		self.assertEqual(links["Transport Locations"], ("Page", "tms-locations"))
		self.assertEqual(links["Data Import"], ("Page", "tms-data-import"))
		self.assertEqual(links["Materials"], ("DocType", "Cargo Types"))
		self.assertEqual(links["Sales Invoice"], ("DocType", "Sales Invoice"))
		self.assertEqual(links["Purchase Invoice"], ("DocType", "Purchase Invoice"))
		self.assertEqual(links["Asset"], ("DocType", "Asset"))

	def test_transport_management_sidebar_excludes_legacy_fleet_items(self):
		items = self.load_sidebar()["items"]
		labels_and_targets = {row.get("label") for row in items} | {row.get("link_to") for row in items}
		for legacy in (
			"Transport Shipment",
			"Trips",
			"Manifest",
			"Trip Routes",
			"Trip Locations",
			"Fuel Requests",
			"Requested Payment",
			"Round Trip",
			"Trip Breakdown",
			"Trailers",
		):
			self.assertNotIn(legacy, labels_and_targets)

	def test_transport_management_sidebar_has_no_duplicate_items(self):
		items = self.load_sidebar()["items"]
		links = [(row.get("label"), row.get("link_type"), row.get("link_to")) for row in items if row["type"] == "Link"]
		self.assertEqual(len(links), len(set(links)))

	def test_transport_management_desktop_icon_points_to_sidebar(self):
		metadata = json.loads(DESKTOP_ICON_PATH.read_text())
		self.assertEqual(metadata["doctype"], "Desktop Icon")
		self.assertEqual(metadata["name"], "Transport Management")
		self.assertEqual(metadata["label"], "Transport Management")
		self.assertEqual(metadata["app"], "transport_management")
		self.assertEqual(metadata["link_type"], "Workspace Sidebar")
		self.assertEqual(metadata["link_to"], "Transport Management")
		self.assertEqual(metadata["hidden"], 0)

	def test_fleet_ms_sidebar_is_not_redefined_by_transport_management(self):
		sidebar = self.load_sidebar()
		self.assertEqual(sidebar["name"], "Transport Management")
		self.assertNotEqual(sidebar["name"], "Fleet MS")
		self.assertFalse(frappe.db.exists("Workspace Sidebar", "Fleet MS"))
