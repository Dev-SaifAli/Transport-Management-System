"""Tests for TMS role-aware login landing behavior."""

import json
from pathlib import Path
import unittest

import frappe
from frappe.website.utils import get_home_page

from transport_management.rbac import ensure_tms_rbac
from transport_management.tms_landing import TRIP_OPERATIONS_HOME, get_tms_home_page

APP_ROOT = Path(__file__).resolve().parents[1]
SIDEBAR_PATH = APP_ROOT / "workspace_sidebar" / "transport_management.json"
LOGIN_CSS_PATH = APP_ROOT / "public" / "css" / "tms_login.css"
LOGIN_JS_PATH = APP_ROOT / "public" / "js" / "tms_login.js"
LOGIN_IMAGE_PATH = APP_ROOT / "public" / "images" / "tms-login-transport.svg"


class TestTMSLanding(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		ensure_tms_rbac()

	def setUp(self):
		frappe.db.savepoint("tms_landing_test")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="tms_landing_test")

	def make_user(self, roles):
		email = f"{frappe.generate_hash(length=10).lower()}@tms-landing.test"
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"enabled": 1,
			"first_name": "TMS Landing",
			"new_password": "TMSLanding#2026",
		})
		for role in roles:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
		frappe.clear_cache(user=email)
		return email

	def test_pure_trip_data_entry_resolves_to_trip_operations(self):
		user = self.make_user(["TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRIP_OPERATIONS_HOME)

	def test_frappe_home_page_resolver_uses_trip_operations_for_pure_trip_user(self):
		user = self.make_user(["TMS Trip Data Entry"])
		frappe.set_user(user)
		frappe.cache.hdel("home_page", user)
		self.assertEqual(get_home_page(), TRIP_OPERATIONS_HOME)

	def test_administrator_is_not_redirected(self):
		self.assertIsNone(get_tms_home_page("Administrator"))

	def test_system_manager_is_not_redirected(self):
		user = self.make_user(["System Manager", "TMS Trip Data Entry"])
		self.assertIsNone(get_tms_home_page(user))

	def test_transport_admin_is_not_redirected(self):
		user = self.make_user(["Transport Admin", "TMS Trip Data Entry"])
		self.assertIsNone(get_tms_home_page(user))

	def test_transport_manager_is_not_redirected(self):
		user = self.make_user(["Transport Manager", "TMS Trip Data Entry"])
		self.assertIsNone(get_tms_home_page(user))

	def test_direct_transport_trip_routes_are_not_part_of_landing_decision(self):
		user = self.make_user(["TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRIP_OPERATIONS_HOME)
		self.assertNotEqual(get_tms_home_page(user), "desk/transport-trip")

	def test_direct_transport_job_routes_are_not_part_of_landing_decision(self):
		user = self.make_user(["TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRIP_OPERATIONS_HOME)
		self.assertNotEqual(get_tms_home_page(user), "desk/transport-job")

	def test_landing_helper_has_no_loop_state(self):
		user = self.make_user(["TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRIP_OPERATIONS_HOME)
		self.assertEqual(get_tms_home_page(user), TRIP_OPERATIONS_HOME)

	def test_sidebar_home_points_to_trip_operations_and_dashboard_link_is_not_duplicated(self):
		sidebar = json.loads(SIDEBAR_PATH.read_text())
		items = sidebar["items"]
		home = next(item for item in items if item.get("label") == "Home")

		self.assertEqual(home.get("link_type"), "Page")
		self.assertEqual(home.get("link_to"), "tms-trip-operations")
		self.assertNotIn("Operations Dashboard", {item.get("label") for item in items})

	def test_dashboard_page_still_exists(self):
		page_path = (
			APP_ROOT
			/ "transport_management"
			/ "page"
			/ "tms_trip_operations"
			/ "tms_trip_operations.json"
		)
		page = json.loads(page_path.read_text())

		self.assertEqual(page.get("doctype"), "Page")
		self.assertEqual(page.get("page_name"), "tms-trip-operations")

	def test_login_customization_assets_are_local_and_scoped(self):
		self.assertTrue(LOGIN_CSS_PATH.exists())
		self.assertTrue(LOGIN_JS_PATH.exists())
		self.assertTrue(LOGIN_IMAGE_PATH.exists())

		css = LOGIN_CSS_PATH.read_text()
		js = LOGIN_JS_PATH.read_text()
		image = LOGIN_IMAGE_PATH.read_text()

		self.assertIn('body[data-path="login"]', css)
		self.assertIn('data-path") === "login"', js)
		self.assertIn("AL RANA TRANSPORT LLC", js)
		self.assertIn("tms-login-transport.svg", css)
		self.assertIn("<svg", image)
