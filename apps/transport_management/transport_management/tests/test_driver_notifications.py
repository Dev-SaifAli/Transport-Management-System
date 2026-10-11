"""Focused tests for Driver Portal trip-assignment notifications."""

import secrets
import unittest
from unittest.mock import patch

import frappe
from frappe.modules import reload_doc

from transport_management.services import driver_notifications
from transport_management.services.driver_portal_auth import AL_RANA_COMPANY


class TestDriverAssignmentNotifications(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_trip", force=True)

	def setUp(self):
		frappe.db.savepoint("driver_assignment_notifications")
		self.old_developer_mode = frappe.conf.get("developer_mode")
		frappe.conf.developer_mode = 1
		driver_notifications.clear_development_notifications()
		self.fixture = self.make_fixture()

	def tearDown(self):
		driver_notifications.clear_development_notifications()
		frappe.conf.developer_mode = self.old_developer_mode
		frappe.db.rollback(save_point="driver_assignment_notifications")

	def make_fixture(self):
		suffix = frappe.generate_hash(length=8)
		number_seed = secrets.randbelow(900000) + 100000
		self.ensure_basics()
		country = frappe.db.get_value("Country", "United Arab Emirates") or frappe.get_all("Country", pluck="name", limit=1)[0]

		driver_a = self.make_driver(f"Notify Driver A {suffix}", f"052{number_seed}")
		driver_b = self.make_driver(f"Notify Driver B {suffix}", f"056{number_seed}")
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": f"Notify Customer {suffix}",
			"customer_type": "Company",
		}).insert(ignore_permissions=True)
		supplier = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": f"Notify Supplier {suffix}",
			"supplier_type": "Company",
			"is_transporter": 1,
			"transporter_status": "Active",
		}).insert(ignore_permissions=True)
		material = frappe.get_doc({
			"doctype": "Cargo Types",
			"cargo_name": f"Notify Material {suffix}",
			"active": 1,
			"allowed_truck_types": [{"truck_type": "TIPPER"}],
		}).insert(ignore_permissions=True)
		loading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"Notify Loading {suffix}",
			"country": country,
			"location_usage": "Loading",
			"location_type": "Plant",
			"active": 1,
		}).insert(ignore_permissions=True)
		unloading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"Notify Unloading {suffix}",
			"country": country,
			"location_usage": "Unloading",
			"location_type": "Customer Site",
			"customer": customer.name,
			"active": 1,
		}).insert(ignore_permissions=True)
		return frappe._dict(
			driver_a=driver_a.name,
			driver_a_mobile=driver_a.cell_number,
			driver_a_employee=driver_a.employee,
			driver_b=driver_b.name,
			driver_b_mobile=driver_b.cell_number,
			driver_b_employee=driver_b.employee,
			customer=customer.name,
			supplier=supplier.name,
			material=material.name,
			loading_site=loading_site.name,
			unloading_site=unloading_site.name,
		)

	def ensure_basics(self):
		if not frappe.db.exists("Gender", "Male"):
			frappe.get_doc({"doctype": "Gender", "gender": "Male"}).insert(ignore_permissions=True)
		if not frappe.db.exists("UOM", "TON"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "TON", "enabled": 1}).insert(ignore_permissions=True)
		if not frappe.db.exists("Truck Type", "TIPPER"):
			frappe.get_doc({"doctype": "Truck Type", "truck_type": "TIPPER"}).insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Company", AL_RANA_COMPANY))

	def make_driver(self, full_name, mobile):
		employee = frappe.get_doc({
			"doctype": "Employee",
			"first_name": full_name,
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2026-01-01",
			"company": AL_RANA_COMPANY,
			"status": "Active",
		}).insert(ignore_permissions=True)
		return frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": full_name,
			"status": "Active",
			"cell_number": mobile,
			"employee": employee.name,
		}).insert(ignore_permissions=True)

	def make_truck(self):
		suffix = frappe.generate_hash(length=8)
		return frappe.get_doc({
			"doctype": "Truck",
			"truck_number": f"NOTIFY-{suffix}",
			"license_plate": f"NOTIFY-{suffix}",
			"vehicle_type": "TIPPER",
			"ownership_type": "OWN",
			"status": "Idle",
			"disabled": 0,
		}).insert(ignore_permissions=True)

	def make_hired_vehicle(self):
		suffix = frappe.generate_hash(length=8)
		return frappe.get_doc({
			"doctype": "Hired Vehicle",
			"transporter": self.fixture.supplier,
			"plate_number": f"HV-NOTIFY-{suffix}",
			"vehicle_type": "TIPPER",
			"active": 1,
		}).insert(ignore_permissions=True)

	def make_job(self):
		return frappe.get_doc({
			"doctype": "Transport Job",
			"customer": self.fixture.customer,
			"requested_date": "2026-10-05",
			"loading_site": self.fixture.loading_site,
			"unloading_site": self.fixture.unloading_site,
			"material": self.fixture.material,
			"requested_quantity": 50,
			"uom": "TON",
		}).insert(ignore_permissions=True)

	def make_trip(self, driver=None, suppress_notification=True, execution_source="OWN"):
		job = self.make_job()
		if execution_source == "HIRED":
			vehicle = self.make_hired_vehicle()
			doc = frappe.get_doc({
				"doctype": "Transport Trip",
				"transport_job": job.name,
				"execution_source": "HIRED",
				"trip_date": job.requested_date,
				"transporter": self.fixture.supplier,
				"hired_vehicle": vehicle.name,
				"loading_site": self.fixture.loading_site,
				"unloading_site": self.fixture.unloading_site,
				"material": self.fixture.material,
				"planned_quantity": 10,
				"uom": "TON",
			})
		else:
			truck = self.make_truck()
			doc = frappe.get_doc({
				"doctype": "Transport Trip",
				"transport_job": job.name,
				"execution_source": "OWN",
				"trip_date": job.requested_date,
				"vehicle": truck.name,
				"driver": driver or self.fixture.driver_a,
				"loading_site": self.fixture.loading_site,
				"unloading_site": self.fixture.unloading_site,
				"material": self.fixture.material,
				"planned_quantity": 10,
				"uom": "TON",
			})

		if suppress_notification:
			with patch(
				"transport_management.services.driver_notifications.queue_driver_trip_assignment_notification"
			):
				doc.insert(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True)
		return doc

	def test_first_driver_assignment_queues_notification(self):
		with patch(
			"transport_management.services.driver_notifications.queue_driver_trip_assignment_notification"
		) as queue:
			trip = self.make_trip(suppress_notification=False)
		queue.assert_called_once_with(trip.name, None)

	def test_saving_same_assigned_driver_again_does_not_resend(self):
		trip = self.make_trip()
		trip.remarks = "Updated remarks"
		with patch(
			"transport_management.services.driver_notifications.queue_driver_trip_assignment_notification"
		) as queue:
			trip.save(ignore_permissions=True)
		queue.assert_not_called()

	def test_changing_driver_notifies_only_new_driver(self):
		trip = self.make_trip()
		trip.driver = self.fixture.driver_b
		with patch(
			"transport_management.services.driver_notifications.queue_driver_trip_assignment_notification"
		) as queue:
			trip.save(ignore_permissions=True)
		queue.assert_called_once_with(trip.name, self.fixture.driver_a)

	def test_creating_trip_without_driver_sends_nothing(self):
		with patch(
			"transport_management.services.driver_notifications.queue_driver_trip_assignment_notification"
		) as queue:
			self.make_trip(suppress_notification=False, execution_source="HIRED")
		queue.assert_not_called()

	def test_removing_driver_sends_nothing(self):
		trip = self.make_trip()
		frappe.db.set_value("Transport Trip", trip.name, "driver", None, update_modified=False)
		trip = frappe.get_doc("Transport Trip", trip.name)
		trip.execution_source = "HIRED"
		trip.vehicle = None
		trip.driver = None
		trip.transporter = self.fixture.supplier
		trip.hired_vehicle = self.make_hired_vehicle().name
		with patch(
			"transport_management.services.driver_notifications.queue_driver_trip_assignment_notification"
		) as queue:
			trip.save(ignore_permissions=True)
		queue.assert_not_called()

	def test_missing_mobile_handled_safely(self):
		frappe.db.set_value("Truck Driver", self.fixture.driver_a, "cell_number", "", update_modified=False)
		trip = self.make_trip()
		result = driver_notifications.notify_driver_trip_assignment(trip.name)
		self.assertEqual(result["status"], "SKIPPED")
		self.assertIn("mobile number is missing", result["error"])

	def test_dummy_mobile_does_not_call_production_sender(self):
		frappe.conf.developer_mode = 0
		frappe.db.set_value("Truck Driver", self.fixture.driver_a, "cell_number", self.get_unused_dummy_mobile(), update_modified=False)
		trip = self.make_trip()
		with patch("transport_management.services.driver_notifications.send_driver_notification") as sender:
			result = driver_notifications.notify_driver_trip_assignment(trip.name)
		sender.assert_not_called()
		self.assertEqual(result["status"], "SKIPPED")

	def get_unused_dummy_mobile(self):
		for index in range(99, 70, -1):
			mobile = f"05000000{index:02d}"
			if not frappe.db.exists("Truck Driver", {"cell_number": mobile}):
				return mobile
		self.fail("No unused dummy mobile number available for test")

	def test_active_linked_al_rana_employee_passes(self):
		trip = self.make_trip()
		result = driver_notifications.notify_driver_trip_assignment(trip.name)
		self.assertEqual(result["status"], "SENT")
		self.assertEqual(
			frappe.db.get_value("Transport Trip", trip.name, "assignment_notification_status"),
			"SENT",
		)
		self.assertTrue(frappe.db.get_value("Transport Trip", trip.name, "assignment_notified_at"))
		notifications = driver_notifications.get_development_notifications()
		self.assertEqual(len(notifications), 1)
		self.assertEqual(notifications[0]["mobile"], self.fixture.driver_a_mobile)

	def test_inactive_employee_is_safely_skipped(self):
		frappe.db.set_value("Employee", self.fixture.driver_a_employee, "status", "Inactive", update_modified=False)
		trip = self.make_trip()
		result = driver_notifications.notify_driver_trip_assignment(trip.name)
		self.assertEqual(result["status"], "SKIPPED")
		self.assertIn("Employee is not active", result["error"])

	def test_notification_message_does_not_contain_commercial_values(self):
		trip = self.make_trip()
		message = driver_notifications.build_trip_assignment_message(
			frappe.db.get_value(
				"Transport Trip",
				trip.name,
				["name", "loading_site", "unloading_site"],
				as_dict=True,
			)
		)
		for forbidden in ("rate", "invoice", "amount", "payable", "salary"):
			self.assertNotIn(forbidden, message.lower())

	def test_notification_status_and_audit_updates_correctly(self):
		trip = self.make_trip()
		result = driver_notifications.notify_driver_trip_assignment(trip.name)
		self.assertEqual(result["status"], "SENT")
		self.assertEqual(frappe.db.get_value("Transport Trip", trip.name, "assignment_notification_error"), "")
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{
					"reference_doctype": "Transport Trip",
					"reference_name": trip.name,
					"content": ["like", "%DRIVER_ASSIGNMENT_NOTIFIED%"],
				},
			)
		)

	def test_provider_failure_does_not_fail_trip_assignment(self):
		trip = self.make_trip()
		with patch(
			"transport_management.services.driver_notifications.send_driver_notification",
			side_effect=RuntimeError("Provider timeout secret-token"),
		):
			result = driver_notifications.notify_driver_trip_assignment(trip.name)
		self.assertEqual(result["status"], "FAILED")
		self.assertIn("Provider timeout", result["error"])
		self.assertEqual(
			frappe.db.get_value("Transport Trip", trip.name, "assignment_notification_status"),
			"FAILED",
		)

	def test_unrelated_trip_edit_does_not_resend(self):
		trip = self.make_trip()
		trip.loading_no = "LOAD-1"
		with patch(
			"transport_management.services.driver_notifications.queue_driver_trip_assignment_notification"
		) as queue:
			trip.save(ignore_permissions=True)
		queue.assert_not_called()
