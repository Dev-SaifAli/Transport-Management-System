"""Focused tests for Driver Portal My Trips API."""

import secrets
import unittest
import zlib
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from transport_management.api import driver_portal
from transport_management.services import driver_portal_auth as auth
from transport_management.services import driver_portal_documents as documents
from transport_management.services import driver_portal_trips as trips


class TestDriverPortalTrips(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		frappe.reload_doc("transport_management", "doctype", "transport_trip", force=True)
		frappe.reload_doc("transport_management", "doctype", "transport_trip_document", force=True)

	def setUp(self):
		frappe.db.savepoint("driver_portal_trips")
		frappe.local.request_ip = "127.0.0.1"
		self.fixture = self.make_fixture()

	def tearDown(self):
		frappe.cache.delete_keys("tms_driver_portal:")
		frappe.db.rollback(save_point="driver_portal_trips")

	def make_fixture(self):
		suffix = frappe.generate_hash(length=8)
		number_seed = secrets.randbelow(900000) + 100000
		self.ensure_basics()
		company = auth.AL_RANA_COMPANY
		country = frappe.db.get_value("Country", "United Arab Emirates") or frappe.get_all("Country", pluck="name", limit=1)[0]

		employee = self.make_employee(f"Portal Trips Driver {suffix}", company)
		driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"Portal Trips Driver {suffix}",
			"status": "Active",
			"cell_number": f"052{number_seed}",
			"employee": employee.name,
		}).insert(ignore_permissions=True)
		other_employee = self.make_employee(f"Other Portal Trips Driver {suffix}", company)
		other_driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"Other Portal Trips Driver {suffix}",
			"status": "Active",
			"cell_number": f"056{number_seed}",
			"employee": other_employee.name,
		}).insert(ignore_permissions=True)
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": f"Portal Trips Customer {suffix}",
			"customer_type": "Company",
		}).insert(ignore_permissions=True)
		material = frappe.get_doc({
			"doctype": "Cargo Types",
			"cargo_name": f"Portal Trips Material {suffix}",
			"active": 1,
			"allowed_truck_types": [{"truck_type": "TIPPER"}],
		}).insert(ignore_permissions=True)
		loading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"Portal Trips Loading {suffix}",
			"country": country,
			"location_usage": "Loading",
			"location_type": "Plant",
			"active": 1,
		}).insert(ignore_permissions=True)
		unloading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"Portal Trips Unloading {suffix}",
			"country": country,
			"location_usage": "Unloading",
			"location_type": "Customer Site",
			"customer": customer.name,
			"active": 1,
		}).insert(ignore_permissions=True)
		return frappe._dict(
			company=company,
			employee=employee.name,
			driver=driver.name,
			mobile=driver.cell_number,
			other_employee=other_employee.name,
			other_driver=other_driver.name,
			customer=customer.name,
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
		self.assertTrue(frappe.db.exists("Company", auth.AL_RANA_COMPANY))

	def make_employee(self, name, company):
		return frappe.get_doc({
			"doctype": "Employee",
			"first_name": name,
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2026-01-01",
			"company": company,
			"status": "Active",
		}).insert(ignore_permissions=True)

	def make_truck(self):
		suffix = frappe.generate_hash(length=8)
		return frappe.get_doc({
			"doctype": "Truck",
			"truck_number": f"PORTAL-{suffix}",
			"license_plate": f"PORTAL-{suffix}",
			"vehicle_type": "TIPPER",
			"ownership_type": "OWN",
			"status": "Idle",
			"disabled": 0,
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

	def make_trip(self, driver=None, status="PLANNED", trip_date="2026-10-05", planned_quantity=10):
		job = self.make_job()
		truck = self.make_truck()
		doc = frappe.get_doc({
			"doctype": "Transport Trip",
			"transport_job": job.name,
			"execution_source": "OWN",
			"trip_date": trip_date,
			"vehicle": truck.name,
			"driver": driver or self.fixture.driver,
			"loading_site": self.fixture.loading_site,
			"unloading_site": self.fixture.unloading_site,
			"material": self.fixture.material,
			"planned_quantity": planned_quantity,
			"uom": "TON",
		}).insert(ignore_permissions=True)
		self.set_trip_status(doc.name, status)
		return doc.name

	def set_trip_status(self, trip, status):
		values = {"status": status}
		if status in {"LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"}:
			values.update({"loaded_quantity": 8, "loading_datetime": "2026-10-05 08:00:00"})
		if status in {"DELIVERED", "POD_RECEIVED", "CLOSED"}:
			values.update({"delivered_quantity": 7, "delivery_datetime": "2026-10-05 18:00:00"})
		if status in {"POD_RECEIVED", "CLOSED"}:
			values.update({"pod_attachment": "/private/files/test-pod.pdf", "pod_received_at": "2026-10-05 19:00:00"})
		for fieldname, value in values.items():
			frappe.db.set_value("Transport Trip", trip, fieldname, value, update_modified=False)

	def make_token(self):
		identity = auth.resolve_driver_identity(self.fixture.mobile)
		self.assertTrue(identity)
		return auth.create_driver_session(identity, self.fixture.mobile)

	def call_get_my_trips(self, token=None, **kwargs):
		token = token or self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			return trips.get_my_trips(**kwargs)

	def test_unauthenticated_request_rejected(self):
		with self.assertRaises(auth.DriverPortalAuthError):
			trips.get_my_trips()

	def test_authenticated_driver_only_receives_own_trips(self):
		own_trip = self.make_trip(status="ASSIGNED")
		self.make_trip(driver=self.fixture.other_driver, status="ASSIGNED")
		result = self.call_get_my_trips(view="all")
		self.assertEqual([row["trip_id"] for row in result["trips"]], [own_trip])

	def test_another_driver_trips_are_not_returned(self):
		self.make_trip(driver=self.fixture.other_driver, status="ASSIGNED")
		result = self.call_get_my_trips(view="all")
		self.assertEqual(result["trips"], [])

	def test_frontend_driver_id_parameter_cannot_override_identity(self):
		own_trip = self.make_trip(status="ASSIGNED")
		self.make_trip(driver=self.fixture.other_driver, status="ASSIGNED")
		result = self.call_get_my_trips(view="all", driver_id=self.fixture.other_driver)
		self.assertEqual([row["trip_id"] for row in result["trips"]], [own_trip])

	def test_no_commercial_or_accounting_fields_leak(self):
		self.make_trip(status="ASSIGNED")
		result = self.call_get_my_trips(view="all")
		row = result["trips"][0]
		for fieldname in {
			"rate",
			"amount",
			"agreed_rate",
			"ordered_amount",
			"transport_sales_invoice",
			"transport_billing_status",
			"supplier",
			"payable_account",
		}:
			self.assertNotIn(fieldname, row)

	def test_active_filter_works(self):
		active_trip = self.make_trip(status="IN_TRANSIT")
		self.make_trip(status="PLANNED")
		self.make_trip(status="CLOSED")
		result = self.call_get_my_trips(view="active")
		self.assertEqual([row["trip_id"] for row in result["trips"]], [active_trip])

	def test_completed_filter_works(self):
		self.make_trip(status="ASSIGNED")
		completed_trip = self.make_trip(status="CLOSED")
		result = self.call_get_my_trips(view="completed")
		self.assertEqual([row["trip_id"] for row in result["trips"]], [completed_trip])

	def test_cancelled_hidden_by_default_and_returned_for_all(self):
		cancelled_trip = self.make_trip(status="CANCELLED")
		default_result = self.call_get_my_trips()
		self.assertNotIn(cancelled_trip, [row["trip_id"] for row in default_result["trips"]])
		all_result = self.call_get_my_trips(view="all")
		self.assertIn(cancelled_trip, [row["trip_id"] for row in all_result["trips"]])

	def test_pagination_works(self):
		first = self.make_trip(status="ASSIGNED", trip_date="2026-10-05")
		second = self.make_trip(status="ASSIGNED", trip_date="2026-10-06")
		result = self.call_get_my_trips(view="all", limit=1, offset=1)
		self.assertEqual(result["limit"], 1)
		self.assertEqual(result["offset"], 1)
		self.assertEqual(result["total"], 2)
		self.assertEqual([row["trip_id"] for row in result["trips"]], [second])
		self.assertNotEqual(first, second)

	def test_empty_result_returns_cleanly(self):
		result = self.call_get_my_trips()
		self.assertTrue(result["ok"])
		self.assertEqual(result["total"], 0)
		self.assertEqual(result["trips"], [])

	def test_linked_employee_identity_still_required(self):
		token = self.make_token()
		frappe.db.set_value("Truck Driver", self.fixture.driver, "employee", "")
		with self.assertRaises(auth.DriverPortalAuthError):
			self.call_get_my_trips(token=token)

	def test_revoked_portal_session_cannot_call_endpoint(self):
		token = self.make_token()
		auth.revoke_driver_session(token)
		with self.assertRaises(auth.DriverPortalAuthError):
			self.call_get_my_trips(token=token)

	def call_get_trip(self, trip_id=None, token=None):
		token = token or self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			return trips.get_trip_detail(trip_id=trip_id)

	def call_start_trip(self, trip_id=None, token=None):
		token = token or self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			return trips.start_driver_trip(trip_id=trip_id)

	def call_mark_delivered(self, trip_id=None, token=None):
		token = token or self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			return trips.mark_driver_trip_delivered(trip_id=trip_id)

	def count_driver_started_comments(self, trip):
		return frappe.db.count(
			"Comment",
			{
				"reference_doctype": "Transport Trip",
				"reference_name": trip,
				"content": ["like", "%DRIVER_TRIP_STARTED%"],
			},
		)

	def count_driver_delivered_comments(self, trip):
		return frappe.db.count(
			"Comment",
			{
				"reference_doctype": "Transport Trip",
				"reference_name": trip,
				"content": ["like", "%DRIVER_TRIP_DELIVERED%"],
			},
		)

	def make_png_content(self, suffix=b""):
		width = 1
		height = 1
		raw = b"\x00\x00\x00\x00\x00"
		compressed = zlib.compress(raw)

		def chunk(name, data):
			return (
				len(data).to_bytes(4, "big")
				+ name
				+ data
				+ zlib.crc32(name + data).to_bytes(4, "big")
			)

		return (
			b"\x89PNG\r\n\x1a\n"
			+ chunk(b"IHDR", width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00")
			+ chunk(b"IDAT", compressed)
			+ chunk(b"IEND", b"")
			+ suffix
		)

	def make_upload_file(self, filename="loading-paper.png", content=None, content_type="image/png"):
		content = self.make_png_content(content or b"")
		return SimpleNamespace(
			filename=filename,
			content_type=content_type,
			read=lambda: content,
		)

	def call_upload_trip_document(self, trip_id=None, document_type="LOADING_PAPER", token=None, file=None):
		token = token or self.make_token()
		file = file or self.make_upload_file()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			return documents.upload_trip_document(
				trip_id=trip_id,
				document_type=document_type,
				file=file,
			)

	def call_get_trip_documents(self, trip_id=None, token=None):
		token = token or self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			return documents.get_trip_documents(trip_id=trip_id)

	def count_driver_document_uploaded_comments(self, trip):
		return frappe.db.count(
			"Comment",
			{
				"reference_doctype": "Transport Trip",
				"reference_name": trip,
				"content": ["like", "%DRIVER_TRIP_DOCUMENT_UPLOADED%"],
			},
		)

	def test_get_trip_unauthenticated_request_rejected(self):
		trip = self.make_trip(status="ASSIGNED")
		with self.assertRaises(auth.DriverPortalAuthError):
			trips.get_trip_detail(trip)

	def test_own_assigned_trip_can_be_opened(self):
		trip = self.make_trip(status="ASSIGNED")
		result = self.call_get_trip(trip)
		self.assertTrue(result["ok"])
		self.assertEqual(result["trip"]["trip_id"], trip)
		self.assertEqual(result["trip"]["status"], "ASSIGNED")
		self.assertEqual(result["trip"]["customer"], frappe.db.get_value("Customer", self.fixture.customer, "customer_name"))
		self.assertEqual(result["trip"]["quantity"], 10)
		self.assertEqual(result["trip"]["uom"], "TON")

	def test_another_driver_trip_cannot_be_opened(self):
		trip = self.make_trip(driver=self.fixture.other_driver, status="ASSIGNED")
		with self.assertRaises(frappe.PermissionError):
			self.call_get_trip(trip)

	def test_changing_trip_id_cannot_bypass_ownership(self):
		self.make_trip(status="ASSIGNED")
		other_trip = self.make_trip(driver=self.fixture.other_driver, status="ASSIGNED")
		with self.assertRaises(frappe.PermissionError):
			self.call_get_trip(other_trip)

	def test_frontend_driver_id_cannot_override_get_trip_identity(self):
		own_trip = self.make_trip(status="ASSIGNED")
		other_trip = self.make_trip(driver=self.fixture.other_driver, status="ASSIGNED")
		token = self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			result = driver_portal.get_trip(trip_id=own_trip, driver_id=self.fixture.other_driver)
		self.assertEqual(result["trip"]["trip_id"], own_trip)
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			with self.assertRaises(frappe.PermissionError):
				driver_portal.get_trip(trip_id=other_trip, driver_id=self.fixture.driver)

	def test_missing_trip_id_rejected(self):
		with self.assertRaises(frappe.PermissionError):
			self.call_get_trip("")

	def test_unknown_trip_handled_cleanly(self):
		with self.assertRaises(frappe.PermissionError):
			self.call_get_trip("TTRIP-2099-99999")

	def test_get_trip_safe_fields_returned(self):
		trip = self.make_trip(status="ASSIGNED")
		result = self.call_get_trip(trip)
		payload = result["trip"]
		for fieldname in {
			"trip_id",
			"trip_date",
			"status",
			"transport_job",
			"customer",
			"material",
			"quantity",
			"uom",
			"loading_location",
			"loading_area_zone",
			"unloading_location",
			"unloading_area_zone",
			"truck",
			"hired_vehicle",
			"loading_datetime",
			"delivery_datetime",
			"driver_started_at",
			"driver_delivered_at",
		}:
			self.assertIn(fieldname, payload)
		self.assertIn("documents", result)
		self.assertIn("required_documents", result)
		self.assertIn("delivery_requirements", result)
		self.assertIn("allowed_actions", result)

	def test_get_trip_commercial_and_accounting_fields_not_leaked(self):
		trip = self.make_trip(status="ASSIGNED")
		result = self.call_get_trip(trip)
		combined = set(result["trip"]) | set(result["documents"]) | set(result)
		for fieldname in {
			"rate",
			"amount",
			"agreed_rate",
			"ordered_amount",
			"transport_sales_invoice",
			"transport_billing_status",
			"payable_account",
			"supplier_rate",
			"salary",
		}:
			self.assertNotIn(fieldname, combined)

	def test_get_trip_allowed_actions_for_key_statuses(self):
		planned = self.make_trip(status="PLANNED")
		assigned = self.make_trip(status="ASSIGNED")
		loaded = self.make_trip(status="LOADED")
		in_transit = self.make_trip(status="IN_TRANSIT")
		delivered = self.make_trip(status="DELIVERED")
		self.assertEqual(self.call_get_trip(planned)["allowed_actions"], [])
		self.assertEqual(self.call_get_trip(assigned)["allowed_actions"], ["START_TRIP"])
		self.assertEqual(self.call_get_trip(loaded)["allowed_actions"], [])
		self.assertEqual(self.call_get_trip(in_transit)["allowed_actions"], ["MARK_DELIVERED"])
		self.assertEqual(self.call_get_trip(delivered)["allowed_actions"], [])

	def test_get_trip_required_documents_returned(self):
		trip = self.make_trip(status="ASSIGNED")
		result = self.call_get_trip(trip)
		self.assertEqual(result["required_documents"][0], "LOADING_PAPER")
		self.assertEqual(result["required_documents"][-1], "OFFLOADING_PAPER")
		self.assertIn("LOADING_PAPER", result["required_documents"])
		self.assertIn("OFFLOADING_PAPER", result["required_documents"])
		self.assertEqual(result["documents"]["document_status"], "MISSING")
		self.assertEqual(result["documents"]["ai_review_status"], "NOT_PROCESSED")

	def test_get_trip_revoked_session_rejected(self):
		trip = self.make_trip(status="ASSIGNED")
		token = self.make_token()
		auth.revoke_driver_session(token)
		with self.assertRaises(auth.DriverPortalAuthError):
			self.call_get_trip(trip, token=token)

	def test_start_trip_unauthenticated_request_rejected(self):
		trip = self.make_trip(status="ASSIGNED")
		with self.assertRaises(auth.DriverPortalAuthError):
			trips.start_driver_trip(trip)

	def test_own_assigned_trip_can_be_started(self):
		trip = self.make_trip(status="ASSIGNED", planned_quantity=12)
		result = self.call_start_trip(trip)
		self.assertTrue(result["ok"])
		self.assertFalse(result["already_started"])
		self.assertEqual(result["trip"]["trip_id"], trip)
		self.assertEqual(result["trip"]["status"], "IN_TRANSIT")
		self.assertTrue(result["trip"]["driver_started_at"])
		self.assertEqual(result["allowed_actions"], ["MARK_DELIVERED"])
		self.assertEqual(frappe.db.get_value("Transport Trip", trip, "status"), "IN_TRANSIT")
		self.assertEqual(frappe.db.get_value("Transport Trip", trip, "loaded_quantity"), 12)
		self.assertTrue(frappe.db.get_value("Transport Trip", trip, "loading_datetime"))

	def test_another_driver_trip_cannot_be_started(self):
		trip = self.make_trip(driver=self.fixture.other_driver, status="ASSIGNED")
		with self.assertRaises(frappe.PermissionError):
			self.call_start_trip(trip)
		self.assertEqual(frappe.db.get_value("Transport Trip", trip, "status"), "ASSIGNED")

	def test_frontend_driver_id_cannot_override_start_trip_identity(self):
		own_trip = self.make_trip(status="ASSIGNED")
		other_trip = self.make_trip(driver=self.fixture.other_driver, status="ASSIGNED")
		token = self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			result = driver_portal.start_trip(trip_id=own_trip, driver_id=self.fixture.other_driver)
		self.assertEqual(result["trip"]["trip_id"], own_trip)
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			with self.assertRaises(frappe.PermissionError):
				driver_portal.start_trip(trip_id=other_trip, driver_id=self.fixture.driver)

	def test_start_trip_missing_trip_id_rejected(self):
		with self.assertRaises(frappe.PermissionError):
			self.call_start_trip("")

	def test_start_trip_planned_trip_rejected(self):
		trip = self.make_trip(status="PLANNED")
		with self.assertRaises(frappe.ValidationError):
			self.call_start_trip(trip)
		self.assertEqual(frappe.db.get_value("Transport Trip", trip, "status"), "PLANNED")

	def test_driver_started_at_is_set_server_side(self):
		trip = self.make_trip(status="ASSIGNED")
		result = self.call_start_trip(trip)
		self.assertTrue(result["trip"]["driver_started_at"])
		self.assertEqual(
			frappe.db.get_value("Transport Trip", trip, "driver_started_at").isoformat(sep=" "),
			result["trip"]["driver_started_at"],
		)

	def test_frontend_timestamp_is_ignored(self):
		trip = self.make_trip(status="ASSIGNED")
		token = self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			result = driver_portal.start_trip(
				trip_id=trip,
				driver_started_at="2000-01-01 00:00:00",
			)
		self.assertNotEqual(result["trip"]["driver_started_at"], "2000-01-01 00:00:00")
		self.assertNotEqual(
			frappe.db.get_value("Transport Trip", trip, "driver_started_at").isoformat(sep=" "),
			"2000-01-01 00:00:00",
		)

	def test_already_started_trip_does_not_restart(self):
		trip = self.make_trip(status="ASSIGNED")
		first = self.call_start_trip(trip)
		first_started_at = first["trip"]["driver_started_at"]
		second = self.call_start_trip(trip)
		self.assertTrue(second["already_started"])
		self.assertEqual(second["trip"]["status"], "IN_TRANSIT")
		self.assertEqual(second["trip"]["driver_started_at"], first_started_at)
		self.assertEqual(frappe.db.get_value("Transport Trip", trip, "driver_started_at").isoformat(sep=" "), first_started_at)

	def test_double_start_request_does_not_duplicate_audit(self):
		trip = self.make_trip(status="ASSIGNED")
		self.call_start_trip(trip)
		self.call_start_trip(trip)
		self.assertEqual(self.count_driver_started_comments(trip), 1)

	def test_start_trip_rejects_delivered_closed_cancelled_and_exception(self):
		for status in ("DELIVERED", "CLOSED", "CANCELLED", "EXCEPTION"):
			trip = self.make_trip(status=status)
			with self.subTest(status=status):
				with self.assertRaises(frappe.ValidationError):
					self.call_start_trip(trip)
				self.assertEqual(frappe.db.get_value("Transport Trip", trip, "status"), status)

	def test_start_trip_creates_driver_started_audit(self):
		trip = self.make_trip(status="ASSIGNED")
		self.call_start_trip(trip)
		comment = frappe.db.get_value(
			"Comment",
			{
				"reference_doctype": "Transport Trip",
				"reference_name": trip,
				"content": ["like", "%DRIVER_TRIP_STARTED%"],
			},
			"content",
		)
		self.assertIn("Source: DRIVER_PORTAL", comment)
		self.assertIn(f"Driver: {self.fixture.driver}", comment)
		self.assertIn(f"Employee: {self.fixture.employee}", comment)
		self.assertIn("Previous Status: ASSIGNED", comment)
		self.assertIn("New Status: IN_TRANSIT", comment)

	def test_start_trip_does_not_resend_assignment_notification(self):
		trip = self.make_trip(status="ASSIGNED")
		with patch(
			"transport_management.services.driver_notifications.queue_driver_trip_assignment_notification"
		) as queue_notification:
			self.call_start_trip(trip)
		queue_notification.assert_not_called()

	def test_start_trip_commercial_and_accounting_fields_not_returned(self):
		trip = self.make_trip(status="ASSIGNED")
		result = self.call_start_trip(trip)
		combined = set(result) | set(result["trip"])
		for fieldname in {
			"rate",
			"amount",
			"agreed_rate",
			"ordered_amount",
			"transport_sales_invoice",
			"transport_billing_status",
			"payable_account",
			"supplier_rate",
			"salary",
		}:
			self.assertNotIn(fieldname, combined)

	def test_upload_trip_document_unauthenticated_request_rejected(self):
		trip = self.make_trip(status="IN_TRANSIT")
		with self.assertRaises(auth.DriverPortalAuthError):
			documents.upload_trip_document(
				trip_id=trip,
				document_type="LOADING_PAPER",
				file=self.make_upload_file(),
			)

	def test_own_trip_document_upload_succeeds(self):
		trip = self.make_trip(status="IN_TRANSIT")
		result = self.call_upload_trip_document(trip)
		self.assertTrue(result["ok"])
		payload = result["document"]
		self.assertEqual(payload["trip_id"], trip)
		self.assertEqual(payload["document_type"], "LOADING_PAPER")
		self.assertEqual(payload["ai_status"], "NOT_PROCESSED")
		self.assertEqual(payload["verification_status"], "PENDING_REVIEW")
		self.assertFalse(payload["can_reupload"])

	def test_another_driver_trip_document_upload_denied(self):
		trip = self.make_trip(driver=self.fixture.other_driver, status="IN_TRANSIT")
		with self.assertRaises(frappe.PermissionError):
			self.call_upload_trip_document(trip)

	def test_frontend_driver_id_cannot_override_upload_identity(self):
		own_trip = self.make_trip(status="IN_TRANSIT")
		other_trip = self.make_trip(driver=self.fixture.other_driver, status="IN_TRANSIT")
		token = self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			result = driver_portal.upload_trip_document(
				trip_id=own_trip,
				document_type="LOADING_PAPER",
				file=self.make_upload_file(),
				driver_id=self.fixture.other_driver,
			)
		self.assertEqual(result["document"]["trip_id"], own_trip)
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			with self.assertRaises(frappe.PermissionError):
				driver_portal.upload_trip_document(
					trip_id=other_trip,
					document_type="LOADING_PAPER",
					file=self.make_upload_file(),
					driver_id=self.fixture.driver,
				)

	def test_upload_trip_document_missing_trip_id_rejected(self):
		with self.assertRaises(frappe.PermissionError):
			self.call_upload_trip_document("")

	def test_upload_trip_document_invalid_document_type_rejected(self):
		trip = self.make_trip(status="IN_TRANSIT")
		with self.assertRaises(frappe.ValidationError):
			self.call_upload_trip_document(trip, document_type="DRIVER_PHOTO")

	def test_upload_trip_document_unsupported_file_rejected(self):
		trip = self.make_trip(status="IN_TRANSIT")
		with self.assertRaises(frappe.ValidationError):
			self.call_upload_trip_document(
				trip,
				file=self.make_upload_file("run.exe", b"MZ", "application/x-msdownload"),
			)

	def test_upload_trip_document_closed_and_cancelled_rejected(self):
		for status in ("CLOSED", "CANCELLED"):
			trip = self.make_trip(status=status)
			with self.subTest(status=status):
				with self.assertRaises(frappe.ValidationError):
					self.call_upload_trip_document(trip)

	def test_upload_trip_document_server_managed_fields_set(self):
		trip = self.make_trip(status="IN_TRANSIT")
		result = self.call_upload_trip_document(trip)
		row = frappe.db.get_value(
			"Transport Trip Document",
			result["document"]["document_id"],
			[
				"uploaded_by_driver",
				"uploaded_by_employee",
				"uploaded_at",
				"upload_source",
				"verification_status",
				"ai_status",
				"file",
			],
			as_dict=True,
		)
		self.assertEqual(row.uploaded_by_driver, self.fixture.driver)
		self.assertEqual(row.uploaded_by_employee, self.fixture.employee)
		self.assertTrue(row.uploaded_at)
		self.assertEqual(row.upload_source, "DRIVER_PORTAL")
		self.assertEqual(row.verification_status, "PENDING_REVIEW")
		self.assertEqual(row.ai_status, "NOT_PROCESSED")
		self.assertTrue(row.file.startswith("/private/files/"))

	def test_upload_trip_document_frontend_cannot_spoof_statuses(self):
		trip = self.make_trip(status="IN_TRANSIT")
		token = self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			result = driver_portal.upload_trip_document(
				trip_id=trip,
				document_type="LOADING_PAPER",
				file=self.make_upload_file(),
				verification_status="APPROVED",
				ai_status="PROCESSED",
			)
		row = frappe.db.get_value(
			"Transport Trip Document",
			result["document"]["document_id"],
			["verification_status", "ai_status"],
			as_dict=True,
		)
		self.assertEqual(row.verification_status, "PENDING_REVIEW")
		self.assertEqual(row.ai_status, "NOT_PROCESSED")

	def test_loading_paper_duplicate_rule_enforced(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(trip, file=self.make_upload_file("loading-1.png", b"one"))
		with self.assertRaises(frappe.DuplicateEntryError):
			self.call_upload_trip_document(trip, file=self.make_upload_file("loading-2.png", b"two"))

	def test_toll_document_multiple_uploads_allowed(self):
		trip = self.make_trip(status="IN_TRANSIT")
		first = self.call_upload_trip_document(
			trip,
			document_type="SHARJAH_TOLL",
			file=self.make_upload_file("toll-1.png", b"one"),
		)
		second = self.call_upload_trip_document(
			trip,
			document_type="SHARJAH_TOLL",
			file=self.make_upload_file("toll-2.png", b"two"),
		)
		self.assertNotEqual(first["document"]["document_id"], second["document"]["document_id"])
		self.assertTrue(first["document"]["can_reupload"])
		self.assertTrue(second["document"]["can_reupload"])

	def test_get_trip_documents_only_returns_own_documents(self):
		own_trip = self.make_trip(status="IN_TRANSIT")
		other_trip = self.make_trip(driver=self.fixture.other_driver, status="IN_TRANSIT")
		self.call_upload_trip_document(own_trip)
		result = self.call_get_trip_documents(own_trip)
		self.assertEqual(result["trip_id"], own_trip)
		self.assertEqual(len(result["documents"]), 1)
		with self.assertRaises(frappe.PermissionError):
			self.call_get_trip_documents(other_trip)

	def test_get_trip_documents_does_not_expose_ai_raw_or_extracted_fields(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(trip)
		result = self.call_get_trip_documents(trip)
		row = result["documents"][0]
		for fieldname in {
			"file",
			"ai_extracted_json",
			"ai_confidence",
			"extracted_amount",
			"extracted_ticket_number",
			"review_notes",
			"verified_by",
			"verified_at",
		}:
			self.assertNotIn(fieldname, row)

	def test_get_trip_document_summary_reflects_uploads(self):
		trip = self.make_trip(status="IN_TRANSIT")
		before = self.call_get_trip(trip)
		self.assertEqual(before["documents"]["document_status"], "MISSING")
		self.call_upload_trip_document(trip, document_type="LOADING_PAPER")
		middle = self.call_get_trip(trip)
		self.assertEqual(middle["documents"]["document_status"], "PARTIAL")
		self.assertEqual(middle["documents"]["loading_paper_status"], "UPLOADED")
		self.assertEqual(middle["documents"]["documents_pending_review"], 1)
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		after = self.call_get_trip(trip)
		self.assertEqual(after["documents"]["document_status"], "COMPLETE")
		self.assertEqual(after["documents"]["offloading_paper_status"], "UPLOADED")

	def test_upload_trip_document_creates_audit_comment(self):
		trip = self.make_trip(status="IN_TRANSIT")
		result = self.call_upload_trip_document(trip)
		self.assertEqual(self.count_driver_document_uploaded_comments(trip), 1)
		comment = frappe.db.get_value(
			"Comment",
			{
				"reference_doctype": "Transport Trip",
				"reference_name": trip,
				"content": ["like", "%DRIVER_TRIP_DOCUMENT_UPLOADED%"],
			},
			"content",
		)
		self.assertIn("Source: DRIVER_PORTAL", comment)
		self.assertIn(f"Document: {result['document']['document_id']}", comment)
		self.assertIn("Document Type: LOADING_PAPER", comment)
		self.assertIn(f"Driver: {self.fixture.driver}", comment)

	def test_upload_trip_document_commercial_and_accounting_fields_not_returned(self):
		trip = self.make_trip(status="IN_TRANSIT")
		result = self.call_upload_trip_document(trip)
		combined = set(result) | set(result["document"])
		for fieldname in {
			"rate",
			"amount",
			"agreed_rate",
			"ordered_amount",
			"transport_sales_invoice",
			"transport_billing_status",
			"payable_account",
			"supplier_rate",
			"salary",
		}:
			self.assertNotIn(fieldname, combined)

	def test_mark_delivered_unauthenticated_request_rejected(self):
		trip = self.make_trip(status="IN_TRANSIT")
		with self.assertRaises(auth.DriverPortalAuthError):
			trips.mark_driver_trip_delivered(trip)

	def test_own_in_transit_trip_can_be_delivered_with_offloading_paper(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		result = self.call_mark_delivered(trip)
		self.assertTrue(result["ok"])
		self.assertFalse(result["already_delivered"])
		self.assertEqual(result["trip"]["trip_id"], trip)
		self.assertEqual(result["trip"]["status"], "DELIVERED")
		self.assertTrue(result["trip"]["driver_delivered_at"])
		self.assertEqual(result["allowed_actions"], [])
		self.assertEqual(frappe.db.get_value("Transport Trip", trip, "status"), "DELIVERED")

	def test_another_driver_trip_cannot_be_delivered(self):
		trip = self.make_trip(driver=self.fixture.other_driver, status="IN_TRANSIT")
		with self.assertRaises(frappe.PermissionError):
			self.call_mark_delivered(trip)

	def test_frontend_driver_id_cannot_override_mark_delivered_identity(self):
		own_trip = self.make_trip(status="IN_TRANSIT")
		other_trip = self.make_trip(driver=self.fixture.other_driver, status="IN_TRANSIT")
		self.call_upload_trip_document(
			own_trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("own-offloading.png", b"own"),
		)
		token = self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			result = driver_portal.mark_delivered(trip_id=own_trip, driver_id=self.fixture.other_driver)
		self.assertEqual(result["trip"]["trip_id"], own_trip)
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			with self.assertRaises(frappe.PermissionError):
				driver_portal.mark_delivered(trip_id=other_trip, driver_id=self.fixture.driver)

	def test_mark_delivered_missing_trip_id_rejected(self):
		with self.assertRaises(frappe.PermissionError):
			self.call_mark_delivered("")

	def test_mark_delivered_rejects_assigned_planned_closed_cancelled_and_exception(self):
		for status in ("ASSIGNED", "PLANNED", "CLOSED", "CANCELLED", "EXCEPTION"):
			trip = self.make_trip(status=status)
			with self.subTest(status=status):
				with self.assertRaises(frappe.ValidationError):
					self.call_mark_delivered(trip)
				self.assertEqual(frappe.db.get_value("Transport Trip", trip, "status"), status)

	def test_mark_delivered_in_transit_without_offloading_paper_rejected(self):
		trip = self.make_trip(status="IN_TRANSIT")
		with self.assertRaises(frappe.ValidationError):
			self.call_mark_delivered(trip)
		self.assertEqual(frappe.local.response.get("error_code"), "OFFLOADING_PAPER_REQUIRED")
		self.assertEqual(frappe.db.get_value("Transport Trip", trip, "status"), "IN_TRANSIT")

	def test_toll_only_document_does_not_satisfy_offloading_requirement(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			trip,
			document_type="SHARJAH_TOLL",
			file=self.make_upload_file("toll-only.png", b"toll"),
		)
		with self.assertRaises(frappe.ValidationError):
			self.call_mark_delivered(trip)
		self.assertEqual(frappe.local.response.get("error_code"), "OFFLOADING_PAPER_REQUIRED")

	def test_offloading_document_must_belong_to_same_trip(self):
		trip = self.make_trip(status="IN_TRANSIT")
		other_trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			other_trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("other-offloading.png", b"other"),
		)
		with self.assertRaises(frappe.ValidationError):
			self.call_mark_delivered(trip)
		self.assertEqual(frappe.local.response.get("error_code"), "OFFLOADING_PAPER_REQUIRED")

	def test_driver_delivered_at_is_set_server_side(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		result = self.call_mark_delivered(trip)
		self.assertTrue(result["trip"]["driver_delivered_at"])
		self.assertEqual(
			frappe.db.get_value("Transport Trip", trip, "driver_delivered_at").isoformat(sep=" "),
			result["trip"]["driver_delivered_at"],
		)

	def test_frontend_delivered_timestamp_is_ignored(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		token = self.make_token()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=token):
			result = driver_portal.mark_delivered(
				trip_id=trip,
				driver_delivered_at="2000-01-01 00:00:00",
				delivered_at="2000-01-01 00:00:00",
			)
		self.assertNotEqual(result["trip"]["driver_delivered_at"], "2000-01-01 00:00:00")
		self.assertNotEqual(
			frappe.db.get_value("Transport Trip", trip, "driver_delivered_at").isoformat(sep=" "),
			"2000-01-01 00:00:00",
		)

	def test_mark_delivered_sets_delivery_datetime_and_quantity_when_missing(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		self.call_mark_delivered(trip)
		row = frappe.db.get_value(
			"Transport Trip",
			trip,
			["delivered_quantity", "loaded_quantity", "delivery_datetime", "driver_delivered_at"],
			as_dict=True,
		)
		self.assertEqual(row.delivered_quantity, row.loaded_quantity)
		self.assertTrue(row.delivery_datetime)
		self.assertTrue(row.driver_delivered_at)

	def test_already_delivered_trip_does_not_redeliver(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		first = self.call_mark_delivered(trip)
		first_delivered_at = first["trip"]["driver_delivered_at"]
		second = self.call_mark_delivered(trip)
		self.assertTrue(second["already_delivered"])
		self.assertEqual(second["trip"]["status"], "DELIVERED")
		self.assertEqual(second["trip"]["driver_delivered_at"], first_delivered_at)
		self.assertEqual(frappe.db.get_value("Transport Trip", trip, "driver_delivered_at").isoformat(sep=" "), first_delivered_at)

	def test_double_mark_delivered_does_not_duplicate_audit(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		self.call_mark_delivered(trip)
		self.call_mark_delivered(trip)
		self.assertEqual(self.count_driver_delivered_comments(trip), 1)

	def test_mark_delivered_creates_driver_delivered_audit(self):
		trip = self.make_trip(status="IN_TRANSIT")
		document = self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		self.call_mark_delivered(trip)
		comment = frappe.db.get_value(
			"Comment",
			{
				"reference_doctype": "Transport Trip",
				"reference_name": trip,
				"content": ["like", "%DRIVER_TRIP_DELIVERED%"],
			},
			"content",
		)
		self.assertIn("Source: DRIVER_PORTAL", comment)
		self.assertIn(f"Driver: {self.fixture.driver}", comment)
		self.assertIn(f"Employee: {self.fixture.employee}", comment)
		self.assertIn("Previous Status: IN_TRANSIT", comment)
		self.assertIn("New Status: DELIVERED", comment)
		self.assertIn(f"Offloading Paper: {document['document']['document_id']}", comment)

	def test_get_trip_reports_delivery_requirements(self):
		trip = self.make_trip(status="IN_TRANSIT")
		before = self.call_get_trip(trip)
		self.assertEqual(
			before["delivery_requirements"],
			{
				"offloading_paper_uploaded": False,
				"can_mark_delivered": False,
				"blocking_reason": "OFFLOADING_PAPER_REQUIRED",
			},
		)
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		after = self.call_get_trip(trip)
		self.assertEqual(
			after["delivery_requirements"],
			{
				"offloading_paper_uploaded": True,
				"can_mark_delivered": True,
				"blocking_reason": None,
			},
		)

	def test_pending_ai_and_review_do_not_block_delivery(self):
		trip = self.make_trip(status="IN_TRANSIT")
		document = self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		row = frappe.db.get_value(
			"Transport Trip Document",
			document["document"]["document_id"],
			["ai_status", "verification_status"],
			as_dict=True,
		)
		self.assertEqual(row.ai_status, "NOT_PROCESSED")
		self.assertEqual(row.verification_status, "PENDING_REVIEW")
		result = self.call_mark_delivered(trip)
		self.assertEqual(result["trip"]["status"], "DELIVERED")

	def test_mark_delivered_commercial_and_accounting_fields_not_returned(self):
		trip = self.make_trip(status="IN_TRANSIT")
		self.call_upload_trip_document(
			trip,
			document_type="OFFLOADING_PAPER",
			file=self.make_upload_file("offloading.png", b"offloading"),
		)
		result = self.call_mark_delivered(trip)
		combined = set(result) | set(result["trip"])
		for fieldname in {
			"rate",
			"amount",
			"agreed_rate",
			"ordered_amount",
			"transport_sales_invoice",
			"transport_billing_status",
			"payable_account",
			"supplier_rate",
			"salary",
		}:
			self.assertNotIn(fieldname, combined)
