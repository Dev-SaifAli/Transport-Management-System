"""Focused tests for Driver Portal OTP authentication."""

import unittest
import secrets
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

from transport_management.services import driver_portal_auth as auth


class TestDriverPortalAuth(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("driver_portal_auth")
		self.old_developer_mode = frappe.conf.get("developer_mode")
		frappe.conf.developer_mode = 1
		frappe.local.request_ip = "127.0.0.1"
		self.fixture = self.make_fixture()

	def tearDown(self):
		self.clear_driver_portal_cache()
		frappe.conf.developer_mode = self.old_developer_mode
		frappe.db.rollback(save_point="driver_portal_auth")

	def clear_driver_portal_cache(self):
		frappe.cache.delete_keys("tms_driver_portal:")

	def make_fixture(self):
		suffix = frappe.generate_hash(length=8)
		number_seed = secrets.randbelow(900000) + 100000
		if not frappe.db.exists("Gender", "Male"):
			frappe.get_doc({"doctype": "Gender", "gender": "Male"}).insert(ignore_permissions=True)

		company = auth.AL_RANA_COMPANY
		self.assertTrue(frappe.db.exists("Company", company), f"{company} is required for Driver Portal tests")

		employee = frappe.get_doc({
			"doctype": "Employee",
			"first_name": f"Portal Driver {suffix}",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2026-01-01",
			"company": company,
			"status": "Active",
		}).insert(ignore_permissions=True)
		driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"Portal Driver {suffix}",
			"status": "Active",
			"cell_number": f"050{number_seed}",
			"employee": employee.name,
		}).insert(ignore_permissions=True)
		other_employee = frappe.get_doc({
			"doctype": "Employee",
			"first_name": f"Other Portal Driver {suffix}",
			"gender": "Male",
			"date_of_birth": "1991-01-01",
			"date_of_joining": "2026-01-01",
			"company": company,
			"status": "Active",
		}).insert(ignore_permissions=True)
		other_driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"Other Portal Driver {suffix}",
			"status": "Active",
			"cell_number": f"055{number_seed}",
			"employee": other_employee.name,
		}).insert(ignore_permissions=True)
		return frappe._dict(
			employee=employee.name,
			driver=driver.name,
			mobile=driver.cell_number,
			other_employee=other_employee.name,
			other_driver=other_driver.name,
			other_mobile=other_driver.cell_number,
		)

	def request_debug_otp(self, mobile=None):
		result = auth.request_driver_otp(mobile or self.fixture.mobile)
		self.assertEqual(result["message"], auth.GENERIC_OTP_MESSAGE)
		return result.get("debug_otp")

	def authenticate(self, mobile=None):
		mobile = mobile or self.fixture.mobile
		otp = self.request_debug_otp(mobile)
		self.assertTrue(otp)
		return auth.verify_driver_otp(mobile, otp)

	def test_registered_active_driver_can_request_otp(self):
		result = auth.request_driver_otp(self.fixture.mobile)
		self.assertTrue(result["ok"])
		self.assertIn("debug_otp", result)
		self.assertNotIn("driver", result)
		self.assertNotIn("employee", result)

	def test_request_otp_does_not_reveal_unknown_mobile(self):
		result = auth.request_driver_otp("0590000000")
		self.assertEqual(result, {"ok": True, "message": auth.GENERIC_OTP_MESSAGE})

	def test_developer_mode_test_otp_can_be_validated(self):
		result = self.authenticate()
		self.assertTrue(result["ok"])
		self.assertEqual(result["driver"]["truck_driver"], self.fixture.driver)
		self.assertEqual(result["driver"]["employee"], self.fixture.employee)
		self.assertTrue(result["token"])

	def test_wrong_otp_rejected(self):
		self.request_debug_otp()
		with self.assertRaises(auth.DriverPortalAuthError):
			auth.verify_driver_otp(self.fixture.mobile, "000000")

	def test_expired_otp_rejected(self):
		otp = self.request_debug_otp()
		key = auth.get_otp_key(self.fixture.mobile)
		challenge = frappe.cache.get_value(key, expires=True)
		challenge["expires_at"] = (now_datetime() - timedelta(seconds=1)).isoformat(sep=" ")
		frappe.cache.set_value(key, challenge, expires_in_sec=auth.OTP_EXPIRY_SECONDS)
		with self.assertRaises(auth.DriverPortalAuthError):
			auth.verify_driver_otp(self.fixture.mobile, otp)

	def test_otp_cannot_be_reused(self):
		otp = self.request_debug_otp()
		auth.verify_driver_otp(self.fixture.mobile, otp)
		with self.assertRaises(auth.DriverPortalAuthError):
			auth.verify_driver_otp(self.fixture.mobile, otp)

	def test_attempt_limit_works(self):
		self.request_debug_otp()
		for _i in range(auth.OTP_MAX_ATTEMPTS):
			with self.assertRaises(auth.DriverPortalAuthError):
				auth.verify_driver_otp(self.fixture.mobile, "111111")
		with self.assertRaises(auth.DriverPortalAuthError):
			auth.verify_driver_otp(self.fixture.mobile, "222222")

	def test_inactive_employee_rejected_safely(self):
		frappe.db.set_value("Employee", self.fixture.employee, "status", "Inactive")
		result = auth.request_driver_otp(self.fixture.mobile)
		self.assertEqual(result, {"ok": True, "message": auth.GENERIC_OTP_MESSAGE})

	def test_truck_driver_without_employee_rejected_safely(self):
		frappe.db.set_value("Truck Driver", self.fixture.driver, "employee", "")
		result = auth.request_driver_otp(self.fixture.mobile)
		self.assertEqual(result, {"ok": True, "message": auth.GENERIC_OTP_MESSAGE})

	def test_duplicate_mobile_configuration_rejected_safely(self):
		drivers = [
			frappe._dict(
				name=self.fixture.driver,
				full_name="Driver One",
				employee=self.fixture.employee,
				status="Active",
				cell_number=self.fixture.mobile,
			),
			frappe._dict(
				name=self.fixture.other_driver,
				full_name="Driver Two",
				employee=self.fixture.other_employee,
				status="Active",
				cell_number=self.fixture.mobile,
			),
		]
		with patch("frappe.get_all", return_value=drivers):
			result = auth.request_driver_otp(self.fixture.mobile)
		self.assertEqual(result, {"ok": True, "message": auth.GENERIC_OTP_MESSAGE})

	def test_get_me_fails_before_authentication(self):
		self.assertIsNone(auth.get_current_driver_from_token(None))
		with self.assertRaises(auth.DriverPortalAuthError):
			auth.get_current_driver()

	def test_get_me_returns_correct_driver_after_authentication(self):
		result = self.authenticate()
		identity = auth.get_current_driver_from_token(result["token"])
		self.assertEqual(identity.truck_driver, self.fixture.driver)
		self.assertEqual(identity.employee, self.fixture.employee)

	def test_get_me_takes_no_driver_id_from_frontend(self):
		result = self.authenticate()
		identity = auth.get_current_driver_from_token(result["token"])
		self.assertNotEqual(identity.truck_driver, self.fixture.other_driver)
		self.assertEqual(identity.truck_driver, self.fixture.driver)

	def test_logout_invalidates_authentication(self):
		result = self.authenticate()
		auth.revoke_driver_session(result["token"])
		self.assertIsNone(auth.get_current_driver_from_token(result["token"]))

	def test_another_driver_identity_cannot_be_selected_by_request_data(self):
		result = self.authenticate()
		with patch("transport_management.services.driver_portal_auth.get_request_token", return_value=result["token"]):
			current = auth.get_current_driver()
		self.assertEqual(current["driver"]["truck_driver"], self.fixture.driver)
		self.assertNotEqual(current["driver"]["truck_driver"], self.fixture.other_driver)
