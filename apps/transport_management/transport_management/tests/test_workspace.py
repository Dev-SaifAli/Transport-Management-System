import json
import unittest
from pathlib import Path

import frappe
from frappe.desk.doctype.number_card.number_card import get_result
from frappe.desk.desktop import get_desktop_page

from transport_management.navigation import sync_tms_navigation
from transport_management.tms_dashboard import get_trips_ready_for_billing


APP_ROOT = Path(frappe.get_app_path("transport_management")).parent
WORKSPACE_PATH = APP_ROOT / "transport_management" / "transport_management" / "workspace" / "transport_management" / "transport_management.json"
HIRED_VEHICLE_PATH = APP_ROOT / "transport_management" / "transport_management" / "doctype" / "hired_vehicle" / "hired_vehicle.json"
PAGE_ROOT = APP_ROOT / "transport_management" / "transport_management" / "page"
SIDEBAR_PATH = APP_ROOT / "transport_management" / "workspace_sidebar" / "tms.json"
DESKTOP_ICON_PATH = APP_ROOT / "transport_management" / "desktop_icon" / "tms.json"

OBSOLETE_WORKSPACES = (
	"AL RANA Operations",
	"AL RANA Dispatcher",
	"AL RANA Expenses",
	"AL RANA Finance",
	"AL RANA HR",
	"AL RANA Admin",
)
OBSOLETE_SIDEBARS = (
	"AL RANA TMS",
	*OBSOLETE_WORKSPACES,
)
TMS_WORKSPACE_ROLES = {
	"System Manager",
	"Transport Admin",
	"Transport Manager",
	"TMS Trip Data Entry",
	"TMS + Expense Data Entry",
	"Expense Approver",
	"Accounts User",
	"Accounts Manager",
	"HR User",
	"HR Manager",
}

TMS_TOOL_PAGES = {
	"tms-data-import": "Transport Management / Data Import",
}


class TestTransportManagementWorkspace(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		sync_tms_navigation()

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
		self.assertEqual({row["role"] for row in workspace["roles"]}, TMS_WORKSPACE_ROLES)

	def test_workspace_is_only_a_home_target_not_a_duplicate_dashboard(self):
		workspace = self.load_workspace()
		content = json.loads(workspace["content"])
		self.assertEqual(
			[item["type"] for item in content],
			["header", "number_card", "number_card", "number_card", "number_card", "header", "quick_list"],
		)
		self.assertEqual(
			[
				block["data"]["number_card_name"]
				for block in content
				if block["type"] == "number_card"
			],
			[
				"Active Transport Jobs",
				"Today's Transport Trips",
				"Trips Awaiting POD",
				"Trips Ready for Billing",
			],
		)
		self.assertEqual(
			content[-1]["data"]["quick_list_name"],
			"Recent Transport Activity",
		)
		self.assertNotIn("Click on", workspace["content"])
		self.assertEqual(workspace["charts"], [])
		self.assertEqual(workspace["custom_blocks"], [])
		self.assertEqual(workspace["links"], [])
		self.assertEqual(
			{card["label"] for card in workspace["number_cards"]},
			{
				"Active Transport Jobs",
				"Today's Transport Trips",
				"Trips Awaiting POD",
				"Trips Ready for Billing",
			},
		)
		self.assertEqual(
			workspace["quick_lists"],
			[
				{
					"document_type": "Transport Trip",
					"label": "Recent Transport Activity",
					"quick_list_filter": "[]",
				}
			],
		)
		self.assertEqual(workspace["shortcuts"], [])

	def test_dashboard_number_cards_are_source_controlled_and_permission_aware(self):
		today_card = json.loads(
			(
				APP_ROOT
				/ "transport_management"
				/ "transport_management"
				/ "number_card"
				/ "today's_transport_trips"
				/ "today's_transport_trips.json"
			).read_text()
		)
		billing_card = json.loads(
			(
				APP_ROOT
				/ "transport_management"
				/ "transport_management"
				/ "number_card"
				/ "trips_ready_for_billing"
				/ "trips_ready_for_billing.json"
			).read_text()
		)

		self.assertEqual(today_card["type"], "Document Type")
		self.assertEqual(today_card["name"], "Today's Transport Trips")
		self.assertEqual(today_card["label"], "Today's Transport Trips")
		self.assertEqual(today_card["document_type"], "Transport Trip")
		self.assertEqual(
			json.loads(today_card["filters_json"]),
			[["Transport Trip", "trip_date", "Timespan", "today"]],
		)
		self.assertEqual(billing_card["type"], "Custom")
		self.assertEqual(billing_card["name"], "Trips Ready for Billing")
		self.assertEqual(billing_card["document_type"], "Transport Trip")
		self.assertEqual(
			billing_card["method"],
			"transport_management.tms_dashboard.get_trips_ready_for_billing",
		)

	def test_workspace_serves_dashboard_cards_and_recent_activity(self):
		page = frappe.as_json(
			{"name": "Transport Management", "title": "Transport Management", "public": 1}
		)
		workspace = get_desktop_page(page)
		self.assertEqual(
			{card.label for card in workspace["number_cards"]["items"]},
			{
				"Active Transport Jobs",
				"Today's Transport Trips",
				"Trips Awaiting POD",
				"Trips Ready for Billing",
			},
		)
		self.assertEqual(
			[(item.document_type, item.label) for item in workspace["quick_lists"]["items"]],
			[("Transport Trip", "Recent Transport Activity")],
		)

	def test_today_card_uses_native_timespan_count(self):
		card = frappe.get_doc("Number Card", "Today's Transport Trips")
		filters = json.loads(card.filters_json)
		result = get_result(card, filters)
		expected = frappe.get_list(
			"Transport Trip",
			filters={"trip_date": ["Timespan", "today"]},
			fields=[{"COUNT": "name", "as": "count"}],
			limit=1,
		)[0]["count"]
		self.assertEqual(result, expected)

	def test_trips_ready_for_billing_count_uses_computed_job_status(self):
		result = get_trips_ready_for_billing()
		ready_jobs = frappe.get_list(
			"Transport Job",
			filters={"billing_status": "Ready for Billing"},
			pluck="name",
			limit=0,
		)
		expected = 0
		if ready_jobs:
			expected = frappe.get_list(
				"Transport Trip",
				filters={
					"transport_job": ["in", ready_jobs],
					"status": "CLOSED",
					"transport_billing_status": "Not Billed",
				},
				fields=[{"COUNT": "name", "as": "count"}],
				limit=1,
			)[0]["count"]
		self.assertEqual(result["value"], expected)

	def test_trips_ready_for_billing_requires_job_and_trip_read_access(self):
		previous_user = frappe.session.user
		try:
			frappe.set_user("Guest")
			with self.assertRaises(frappe.PermissionError):
				get_trips_ready_for_billing()
		finally:
			frappe.set_user(previous_user)

	def test_obsolete_workspaces_are_retired_without_deleting_records(self):
		for workspace_name in OBSOLETE_WORKSPACES:
			folder = frappe.scrub(workspace_name)
			path = APP_ROOT / "transport_management" / "transport_management" / "workspace" / folder / f"{folder}.json"
			self.assertFalse(path.exists(), workspace_name)

			if frappe.db.exists("Workspace", workspace_name):
				doc = frappe.get_doc("Workspace", workspace_name)
				self.assertEqual(doc.public, 0, workspace_name)
				self.assertEqual(doc.is_hidden, 1, workspace_name)

	def test_hired_vehicle_has_searchable_plate_metadata(self):
		metadata = json.loads(HIRED_VEHICLE_PATH.read_text())
		self.assertEqual(metadata["title_field"], "plate_number")
		self.assertEqual(metadata["search_fields"], "plate_number,transporter")

	def test_tms_tool_pages_exist_and_belong_to_transport_management(self):
		for page_name, title in TMS_TOOL_PAGES.items():
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
		self.assertEqual(metadata["roles"], [{"role": "System Manager"}, {"role": "Transport Admin"}])

	def test_tms_owned_doctypes_remain_direct_workspace_links(self):
		workspace = self.load_sidebar()
		direct_links = {
			row.get("link_to"): row.get("link_type")
			for row in workspace["items"]
			if row["type"] == "Link"
		}
		self.assertEqual(direct_links["Transport Job"], "DocType")
		self.assertEqual(direct_links["Transport Trip"], "DocType")
		self.assertEqual(direct_links["Truck"], "DocType")
		self.assertEqual(direct_links["Hired Vehicle"], "DocType")
		self.assertEqual(direct_links["Truck Driver"], "DocType")
		self.assertEqual(direct_links["Transport Location"], "DocType")

	def load_sidebar(self):
		return json.loads(SIDEBAR_PATH.read_text())

	def test_transport_management_workspace_sidebar_metadata(self):
		sidebar = self.load_sidebar()
		self.assertEqual(sidebar["doctype"], "Workspace Sidebar")
		self.assertEqual(sidebar["name"], "TMS")
		self.assertEqual(sidebar["title"], "TMS")
		self.assertEqual(sidebar["module"], "Transport Management")
		self.assertEqual(sidebar["app"], "transport_management")
		self.assertEqual(sidebar["standard"], 1)

	def test_module_sidebar_placeholder_prevents_default_navigation(self):
		path = APP_ROOT / "transport_management" / "workspace_sidebar" / "transport_management.json"
		sidebar = json.loads(path.read_text())
		self.assertEqual(sidebar["name"], "Transport Management")
		self.assertEqual(sidebar["module"], "Transport Management")
		self.assertEqual(sidebar["items"], [])
		self.assertEqual(frappe.get_all("Workspace Sidebar Item", filters={"parent": "Transport Management"}), [])

	def test_obsolete_role_sidebars_are_not_synced(self):
		for sidebar_name in OBSOLETE_SIDEBARS:
			path = APP_ROOT / "transport_management" / "workspace_sidebar" / f"{frappe.scrub(sidebar_name)}.json"
			self.assertFalse(path.exists(), sidebar_name)
			self.assertFalse(frappe.db.exists("Workspace Sidebar", sidebar_name), sidebar_name)

	def test_transport_management_sidebar_links(self):
		items = self.load_sidebar()["items"]
		sections = [row["label"] for row in items if row["type"] == "Section Break"]
		self.assertEqual(sections, ["Operations / Commercial", "Fleet", "Masters", "Tools"])
		section_icons = {
			row["label"]: row["icon"]
			for row in items
			if row["type"] == "Section Break"
		}
		self.assertEqual(section_icons, {
			"Operations / Commercial": "briefcase",
			"Fleet": "truck",
			"Masters": "settings",
			"Tools": "settings",
		})

		links = {row["label"]: (row.get("link_type"), row.get("link_to")) for row in items if row["type"] == "Link"}
		self.assertEqual(links["Home"], ("Workspace", "Transport Management"))
		self.assertEqual(links["Sales Orders"], ("DocType", "Transport Sales Order"))
		self.assertEqual(links["Transport Job"], ("DocType", "Transport Job"))
		self.assertEqual(links["Transport Trip"], ("DocType", "Transport Trip"))
		self.assertEqual(links["Owned Trucks"], ("DocType", "Truck"))
		self.assertEqual(links["Hired Vehicles"], ("DocType", "Hired Vehicle"))
		self.assertEqual(links["Drivers"], ("DocType", "Truck Driver"))
		self.assertEqual(links["Customers"], ("DocType", "Customer"))
		self.assertEqual(links["Suppliers / Transporters"], ("DocType", "Supplier"))
		self.assertEqual(links["Transport Rates"], ("DocType", "Transport Rate"))
		self.assertEqual(links["Transport Charge Rule"], ("DocType", "Transport Charge Rule"))
		self.assertEqual(links["Transport Locations"], ("DocType", "Transport Location"))
		self.assertEqual(links["Data Import"], ("Page", "tms-data-import"))
		self.assertEqual(links["Materials"], ("DocType", "Cargo Types"))
		self.assertEqual(links["Truck Types"], ("DocType", "Truck Type"))
		self.assertNotIn("Sales Invoice", links)
		self.assertNotIn("Purchase Invoice", links)
		self.assertNotIn("Asset", links)

		for item in items:
			if item["type"] != "Link" or not item.get("link_to"):
				continue
			self.assertTrue(
				frappe.db.exists(item["link_type"], item["link_to"]),
				f"Broken sidebar target: {item['link_type']} {item['link_to']}",
			)

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
		self.assertEqual(metadata["name"], "TMS")
		self.assertEqual(metadata["label"], "TMS")
		self.assertEqual(metadata["app"], "transport_management")
		self.assertEqual(metadata["link_type"], "Workspace Sidebar")
		self.assertEqual(metadata["link_to"], "TMS")
		self.assertEqual(metadata["hidden"], 0)
		self.assertEqual({row["role"] for row in metadata["roles"]}, TMS_WORKSPACE_ROLES)

	def test_fleet_ms_sidebar_is_not_redefined_by_transport_management(self):
		sidebar = self.load_sidebar()
		self.assertEqual(sidebar["name"], "TMS")
		self.assertNotEqual(sidebar["name"], "Fleet MS")
		self.assertFalse(frappe.db.exists("Workspace Sidebar", "Fleet MS"))
