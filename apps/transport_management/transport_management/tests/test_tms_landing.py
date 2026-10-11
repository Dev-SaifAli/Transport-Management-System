"""Tests for TMS role-aware login landing behavior."""

import json
from pathlib import Path
import unittest

import frappe
from frappe.website.utils import get_home_page

from transport_management.rbac import ensure_tms_rbac
from transport_management.tms_landing import NATIVE_DESK_HOME, TRANSPORT_MANAGEMENT_HOME, get_tms_home_page

APP_ROOT = Path(__file__).resolve().parents[1]
SIDEBAR_PATH = APP_ROOT / "workspace_sidebar" / "tms.json"
LOGIN_CSS_PATH = APP_ROOT / "public" / "css" / "al_rana_login.css"
LOGIN_JS_PATH = APP_ROOT / "public" / "js" / "al_rana_login.js"
LOGIN_IMAGE_PATH = APP_ROOT / "public" / "images" / "al-rana-hero.webp"
LOGIN_TEMPLATE_PATH = APP_ROOT / "www" / "login.html"


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

	def test_pure_trip_data_entry_resolves_to_transport_management_workspace(self):
		user = self.make_user(["TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRANSPORT_MANAGEMENT_HOME)

	def test_frappe_home_page_resolver_uses_transport_management_workspace_for_pure_trip_user(self):
		user = self.make_user(["TMS Trip Data Entry"])
		frappe.set_user(user)
		frappe.cache.hdel("home_page", user)
		self.assertEqual(get_home_page(), TRANSPORT_MANAGEMENT_HOME)

	def test_administrator_is_not_redirected(self):
		self.assertIsNone(get_tms_home_page("Administrator"))

	def test_system_manager_with_tms_role_uses_native_workspace(self):
		user = self.make_user(["System Manager", "TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRANSPORT_MANAGEMENT_HOME)

	def test_transport_admin_uses_native_desk(self):
		user = self.make_user(["Transport Admin", "TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), NATIVE_DESK_HOME)

	def test_transport_manager_uses_native_workspace(self):
		user = self.make_user(["Transport Manager", "TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRANSPORT_MANAGEMENT_HOME)

	def test_direct_transport_trip_routes_are_not_part_of_landing_decision(self):
		user = self.make_user(["TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRANSPORT_MANAGEMENT_HOME)
		self.assertNotEqual(get_tms_home_page(user), "desk/transport-trip")

	def test_direct_transport_job_routes_are_not_part_of_landing_decision(self):
		user = self.make_user(["TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRANSPORT_MANAGEMENT_HOME)
		self.assertNotEqual(get_tms_home_page(user), "desk/transport-job")

	def test_landing_helper_has_no_loop_state(self):
		user = self.make_user(["TMS Trip Data Entry"])
		self.assertEqual(get_tms_home_page(user), TRANSPORT_MANAGEMENT_HOME)
		self.assertEqual(get_tms_home_page(user), TRANSPORT_MANAGEMENT_HOME)

	def test_sidebar_home_points_to_transport_management_workspace_and_dashboard_link_is_not_duplicated(self):
		sidebar = json.loads(SIDEBAR_PATH.read_text())
		items = sidebar["items"]
		home = next(item for item in items if item.get("label") == "Home")

		self.assertEqual(home.get("link_type"), "Workspace")
		self.assertEqual(home.get("link_to"), "Transport Management")
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
		self.assertTrue(LOGIN_TEMPLATE_PATH.exists())

		css = LOGIN_CSS_PATH.read_text()
		js = LOGIN_JS_PATH.read_text()
		template = LOGIN_TEMPLATE_PATH.read_text()

		self.assertIn('body[data-path="login"]', css)
		self.assertIn("al_rana_login.css", template)
		self.assertIn("al_rana_login.js", template)
		self.assertIn("al-rana-hero.webp", template)
		self.assertIn("AL RANA TMS", template)
		self.assertIn("Login with Email Link", js)
		self.assertIn(".btn-login-with-email-link", css)
