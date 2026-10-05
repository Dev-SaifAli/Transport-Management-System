"""Focused tests for the TMS Trip Operations dashboard."""

import inspect
import json
import unittest
from pathlib import Path

import frappe
from frappe.utils import add_days, today

from transport_management.tms_dashboard import (
	ACTIVE_TRIP_LIMIT,
	get_trip_operations_dashboard,
)


APP_ROOT = Path(frappe.get_app_path("transport_management")).parent
PAGE_PATH = (
	APP_ROOT
	/ "transport_management"
	/ "transport_management"
	/ "page"
	/ "tms_trip_operations"
	/ "tms_trip_operations.json"
)


class TestTMSTripOperationsDashboard(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("tms_trip_operations_dashboard")
		self.fixture = self.make_fixture()
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="tms_trip_operations_dashboard")

	def make_fixture(self):
		suffix = frappe.generate_hash(length=8)
		country = frappe.db.get_value("Country", "United Arab Emirates") or frappe.db.get_value("Country", {})
		self.ensure_uom("TON")
		truck_type = self.ensure_truck_type("TIPPER")
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": f"TMS Dashboard Customer {suffix}",
			"customer_type": "Company",
		}).insert(ignore_permissions=True)
		supplier = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": f"TMS Dashboard Transporter {suffix}",
			"supplier_type": "Company",
			"is_transporter": 1,
			"transporter_status": "Active",
		}).insert(ignore_permissions=True)
		material = frappe.get_doc({
			"doctype": "Cargo Types",
			"cargo_name": f"TMS Dashboard Material {suffix}",
			"active": 1,
			"allowed_truck_types": [{"truck_type": truck_type}],
		}).insert(ignore_permissions=True)
		loading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"TMS Dashboard Loading {suffix}",
			"country": country,
			"location_usage": "Loading",
			"location_type": "Plant",
			"active": 1,
		}).insert(ignore_permissions=True)
		unloading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"TMS Dashboard Unloading {suffix}",
			"country": country,
			"location_usage": "Unloading",
			"location_type": "Customer Site",
			"customer": customer.name,
			"active": 1,
		}).insert(ignore_permissions=True)
		driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"TMS Dashboard Driver {suffix}",
			"status": "Active",
			"cell_number": f"DASH-{suffix}",
		}).insert(ignore_permissions=True)
		truck = frappe.get_doc({
			"doctype": "Truck",
			"truck_number": f"TMS-DASH-{suffix}",
			"license_plate": f"TMS-DASH-{suffix}",
			"vehicle_type": truck_type,
			"ownership_type": "OWN",
			"status": "Idle",
			"disabled": 0,
		}).insert(ignore_permissions=True)
		hired_vehicle = frappe.get_doc({
			"doctype": "Hired Vehicle",
			"transporter": supplier.name,
			"plate_number": f"HV-DASH-{suffix}",
			"vehicle_type": truck_type,
			"active": 1,
		}).insert(ignore_permissions=True)
		job = frappe.get_doc({
			"doctype": "Transport Job",
			"customer": customer.name,
			"requested_date": today(),
			"loading_site": loading_site.name,
			"unloading_site": unloading_site.name,
			"material": material.name,
			"requested_quantity": 30,
			"uom": "TON",
		}).insert(ignore_permissions=True)
		return {
			"customer": customer.name,
			"transporter": supplier.name,
			"material": material.name,
			"loading_site": loading_site.name,
			"unloading_site": unloading_site.name,
			"driver": driver.name,
			"truck": truck.name,
			"hired_vehicle": hired_vehicle.name,
			"job": job.name,
		}

	def ensure_uom(self, uom):
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom, "enabled": 1}).insert(ignore_permissions=True)

	def ensure_truck_type(self, truck_type):
		if not frappe.db.exists("Truck Type", truck_type):
			frappe.get_doc({"doctype": "Truck Type", "truck_type": truck_type}).insert(ignore_permissions=True)
		return truck_type

	def make_trip(self, status="PLANNED", trip_date=None):
		trip = frappe.get_doc({
			"doctype": "Transport Trip",
			"transport_job": self.fixture["job"],
			"execution_source": "HIRED",
			"trip_date": trip_date or today(),
			"transporter": self.fixture["transporter"],
			"hired_vehicle": self.fixture["hired_vehicle"],
			"loading_site": self.fixture["loading_site"],
			"unloading_site": self.fixture["unloading_site"],
			"material": self.fixture["material"],
			"planned_quantity": 1,
			"uom": "TON",
		}).insert(ignore_permissions=True)
		if status != "PLANNED":
			frappe.db.set_value("Transport Trip", trip.name, "status", status, update_modified=True)
			trip.reload()
		return trip

	def make_user_without_tms_access(self):
		email = f"{frappe.generate_hash(length=10).lower()}@tms-dashboard.test"
		frappe.get_doc({
			"doctype": "User",
			"email": email,
			"enabled": 1,
			"first_name": "No TMS Access",
			"new_password": "TMSDash#2026",
		}).insert(ignore_permissions=True)
		frappe.clear_cache(user=email)
		return email

	def count_trips(self, filters):
		rows = frappe.get_list("Transport Trip", filters=filters, fields=[{"COUNT": "name", "as": "count"}], limit=1)
		return frappe.utils.cint(rows[0].get("count") if rows else 0)

	def test_page_metadata_exists_with_expected_roles(self):
		metadata = json.loads(PAGE_PATH.read_text())
		self.assertEqual(metadata["doctype"], "Page")
		self.assertEqual(metadata["name"], "tms-trip-operations")
		self.assertEqual(metadata["page_name"], "tms-trip-operations")
		self.assertEqual(metadata["module"], "Transport Management")
		self.assertEqual(metadata["standard"], "Yes")
		self.assertEqual(
			{row["role"] for row in metadata["roles"]},
			{"TMS Trip Data Entry", "Transport Manager", "Transport Admin", "System Manager"},
		)

	def test_endpoint_rejects_user_without_transport_trip_read(self):
		frappe.set_user(self.make_user_without_tms_access())
		with self.assertRaises(frappe.PermissionError):
			get_trip_operations_dashboard()

	def test_kpi_payload_contains_required_keys_and_uses_expected_filters(self):
		self.make_trip(status="PLANNED", trip_date=today())
		self.make_trip(status="PLANNED", trip_date=add_days(today(), -1))
		self.make_trip(status="IN_TRANSIT")
		self.make_trip(status="DELIVERED")

		payload = get_trip_operations_dashboard()

		self.assertEqual(set(payload["kpis"]), {"today", "planned", "in_transit", "pod_pending"})
		self.assertEqual(payload["kpis"]["today"], self.count_trips({"trip_date": today()}))
		self.assertEqual(payload["kpis"]["planned"], self.count_trips({"status": "PLANNED"}))
		self.assertEqual(payload["kpis"]["in_transit"], self.count_trips({"status": "IN_TRANSIT"}))
		self.assertEqual(payload["kpis"]["pod_pending"], self.count_trips({"status": "DELIVERED"}))

	def test_active_trips_exclude_closed_and_cancelled(self):
		active = self.make_trip(status="PLANNED")
		closed = self.make_trip(status="CLOSED")
		cancelled = self.make_trip(status="CANCELLED")

		payload = get_trip_operations_dashboard()
		active_trip_names = {row["trip"] for row in payload["active_trips"]}

		self.assertIn(active.name, active_trip_names)
		self.assertNotIn(closed.name, active_trip_names)
		self.assertNotIn(cancelled.name, active_trip_names)

	def test_attention_trips_include_exception_and_delivered_only(self):
		exception = self.make_trip(status="EXCEPTION")
		delivered = self.make_trip(status="DELIVERED")
		planned = self.make_trip(status="PLANNED")

		payload = get_trip_operations_dashboard()
		attention = {row["trip"]: row for row in payload["attention_trips"]}

		self.assertEqual(attention[exception.name]["issue"], "Exception")
		self.assertEqual(attention[delivered.name]["issue"], "POD Pending")
		self.assertNotIn(planned.name, attention)

	def test_no_stale_24_hour_logic_exists(self):
		source = inspect.getsource(get_trip_operations_dashboard)
		self.assertNotIn("24", source)
		self.assertNotIn("stale", source.lower())

	def test_results_are_limited(self):
		for _index in range(ACTIVE_TRIP_LIMIT + 3):
			self.make_trip(status="PLANNED")

		payload = get_trip_operations_dashboard()

		self.assertLessEqual(len(payload["active_trips"]), ACTIVE_TRIP_LIMIT)

	def test_quick_action_permissions_reflect_doctype_permissions(self):
		payload = get_trip_operations_dashboard()
		self.assertEqual(payload["permissions"]["can_create_trip"], frappe.has_permission("Transport Trip", ptype="create"))
		self.assertEqual(payload["permissions"]["can_read_trip"], frappe.has_permission("Transport Trip", ptype="read"))
		self.assertEqual(payload["permissions"]["can_read_job"], frappe.has_permission("Transport Job", ptype="read"))
