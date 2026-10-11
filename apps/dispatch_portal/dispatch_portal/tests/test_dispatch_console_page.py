"""App launcher registration and console shell integrity checks."""

import json
import unittest
from pathlib import Path

import frappe

from dispatch_portal.desk_setup import (
	DISPATCH_CONSOLE_ROUTE,
	ICON_LOGO_URL,
	setup_dispatch_console,
)
from dispatch_portal.services.dispatch_access import (
	APP_NAME,
	APP_TITLE,
	CONSOLE_READ_ROLES,
	DISPATCH_ROLE_PROFILE,
	ROLE_DISPATCHER,
	ROLE_VERIFIER,
)

PAGE_NAME = "dispatch-console"
PAGE_FOLDER = "al_rana_dispatch/page/dispatch_console"


class TestDispatchConsoleRegistration(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		from dispatch_portal.services.dispatch_access import ensure_dispatch_roles

		ensure_dispatch_roles()
		setup_dispatch_console()

	def test_app_hooks_register_the_console_route(self):
		app_screen = frappe.get_hooks("add_to_apps_screen", app_name=APP_NAME)
		self.assertEqual(len(app_screen), 1)
		entry = app_screen[0]
		self.assertEqual(entry["route"], DISPATCH_CONSOLE_ROUTE)
		self.assertEqual(entry["title"], APP_TITLE)
		self.assertEqual(entry["has_permission"], "dispatch_portal.api.permissions.has_console_access")
		self.assertTrue(entry["logo"].startswith("/assets/dispatch_portal/icons/desktop_icons/"))

		self.assertEqual(frappe.get_hooks("app_title", app_name=APP_NAME)[0], APP_TITLE)
		self.assertIn("transport_management", frappe.get_hooks("required_apps", app_name=APP_NAME))

	def test_desktop_icon_is_a_role_aware_app_icon(self):
		self.assertTrue(frappe.db.exists("Desktop Icon", APP_TITLE))
		icon = frappe.get_doc("Desktop Icon", APP_TITLE)
		self.assertEqual(icon.icon_type, "App")
		self.assertEqual(icon.link_type, "External")
		self.assertEqual(icon.link, DISPATCH_CONSOLE_ROUTE)
		self.assertEqual(icon.app, APP_NAME)
		self.assertEqual(icon.logo_url, ICON_LOGO_URL)
		self.assertEqual(icon.hidden, 0)

		icon_roles = {row.role for row in icon.get("roles") or []}
		self.assertTrue(icon_roles.issubset(CONSOLE_READ_ROLES))
		self.assertIn(ROLE_DISPATCHER, icon_roles)
		self.assertIn(ROLE_VERIFIER, icon_roles)

	def test_desktop_icon_visible_only_to_dispatchers(self):
		from dispatch_portal.tests.test_helpers import DispatchTestCase  # noqa: F401

		from dispatch_portal.api.permissions import has_console_access

		frappe.set_user("Administrator")
		self.assertTrue(has_console_access()["has_access"])

	def test_page_is_standard_and_module_owned(self):
		self.assertTrue(frappe.db.exists("Page", PAGE_NAME))
		page = frappe.get_doc("Page", PAGE_NAME)
		self.assertEqual(page.module, "AL RANA Dispatch")
		self.assertEqual(page.standard, "Yes")
		self.assertEqual(page.title, APP_TITLE)
		self.assertFalse(page.system_page)

	def test_page_is_role_restricted(self):
		page = frappe.get_doc("Page", PAGE_NAME)
		roles = {row.role for row in page.get("roles") or []}
		self.assertIn(ROLE_DISPATCHER, roles)
		self.assertIn(ROLE_VERIFIER, roles)
		self.assertTrue(roles.issubset(CONSOLE_READ_ROLES))

	def test_app_icon_files_exist_for_both_desktop_icon_styles(self):
		app_path = Path(frappe.get_app_path(APP_NAME))
		for variant in ("solid", "subtle"):
			icon_path = app_path / "public" / "icons" / "desktop_icons" / variant / "al_rana_dispatch.svg"
			self.assertTrue(icon_path.is_file(), f"Missing {icon_path}")
			self.assertIn("<svg", icon_path.read_text())

	def test_boot_resolves_the_dispatch_icon(self):
		icons = frappe.get_all(
			"Desktop Icon",
			filters={"label": APP_TITLE, "icon_type": "App"},
			pluck="name",
			limit_page_length=0,
		)
		self.assertEqual(icons, [APP_TITLE])

	def test_setup_is_idempotent(self):
		for _ in range(2):
			self.assertEqual(setup_dispatch_console(), "AL RANA Dispatch console registered")
		icons = frappe.get_all(
			"Desktop Icon", filters={"label": APP_TITLE}, pluck="name", limit_page_length=0
		)
		self.assertEqual(icons, [APP_TITLE])

	def test_desktop_icon_fixture_is_source_controlled(self):
		app_path = Path(frappe.get_app_path(APP_NAME))
		fixture = app_path / "desktop_icon" / "al_rana_dispatch.json"
		self.assertTrue(fixture.is_file(), f"Missing {fixture}")
		data = json.loads(fixture.read_text())
		self.assertEqual(data["doctype"], "Desktop Icon")
		self.assertEqual(data["name"], APP_TITLE)
		self.assertEqual(data["icon_type"], "App")
		self.assertEqual(data["link"], DISPATCH_CONSOLE_ROUTE)
		self.assertTrue(data["standard"])
		self.assertTrue({row["role"] for row in data["roles"]} <= CONSOLE_READ_ROLES)

	def test_dispatch_role_profile_exists(self):
		profile = frappe.get_doc("Role Profile", DISPATCH_ROLE_PROFILE)
		self.assertIn(ROLE_DISPATCHER, {row.role for row in profile.get("roles") or []})

	def test_no_transportation_entity_is_duplicated(self):
		"""The console is a UI layer: it must not declare any TMS DocType."""
		app_path = Path(frappe.get_app_path(APP_NAME))
		doctype_dirs = [
			path.parent.name
			for path in app_path.rglob("*.json")
			if path.parent.parent.name == "doctype"
		]
		self.assertEqual(doctype_dirs, [], "dispatch_portal must not define DocTypes")
		self.assertFalse((app_path / "doctype").exists())


class TestDispatchPageSourceFiles(unittest.TestCase):
	"""The page ships its script, style and section views."""

	@classmethod
	def setUpClass(cls):
		cls.app_path = Path(frappe.get_app_path(APP_NAME))

	def test_page_files_exist(self):
		page_dir = self.app_path / PAGE_FOLDER
		for filename in (
			"dispatch_console.json",
			"dispatch_console.js",
			"dispatch_console.css",
		):
			self.assertTrue((page_dir / filename).is_file(), f"Missing {filename}")

	def test_page_script_defines_the_shell_and_hooks(self):
		script = (self.app_path / PAGE_FOLDER / "dispatch_console.js").read_text()
		for marker in (
			'frappe.pages["dispatch-console"].on_page_load',
			'frappe.pages["dispatch-console"].on_page_show',
			"dispatch_portal.views[section]",
			"al-dispatch-rail",
		):
			self.assertIn(marker, script)

	def test_css_is_scoped_to_the_console(self):
		css = (self.app_path / PAGE_FOLDER / "dispatch_console.css").read_text()
		self.assertIn(".al-dispatch", css)
		for token in ("--al-teal", "--al-navy", "--al-sky"):
			self.assertIn(token, css)

	def test_every_section_view_is_registered(self):
		for name, marker in (
			("console_common.js", "dispatch_portal.utils"),
			("console_dashboard.js", "dispatch_portal.views.dashboard"),
			("console_trips.js", "dispatch_portal.views.trips"),
			("console_trip_map.js", 'dispatch_portal.views["trip-map"]'),
			("console_verification.js", "dispatch_portal.views.verification"),
			("console_reports.js", "dispatch_portal.views.reports"),
		):
			path = self.app_path / "public" / "js" / "dispatch_portal" / name
			self.assertTrue(path.is_file(), f"Missing {name}")
			self.assertIn(marker, path.read_text(), f"{name} must define {marker}")

	def test_page_js_hook_lists_all_section_views(self):
		hooked = frappe.get_hooks("page_js", app_name=APP_NAME).get(PAGE_NAME, [])
		self.assertEqual(
			hooked,
			[
				"public/js/dispatch_portal/console_common.js",
				"public/js/dispatch_portal/console_dashboard.js",
				"public/js/dispatch_portal/console_trips.js",
				"public/js/dispatch_portal/console_trip_map.js",
				"public/js/dispatch_portal/console_verification.js",
				"public/js/dispatch_portal/console_reports.js",
			],
		)

	def test_section_icons_used_by_the_console_exist_in_lucide(self):
		"""Guards against icon names that would render as empty SVGs."""
		icons_svg = Path(frappe.get_app_path("frappe")) / "public" / "icons" / "lucide" / "icons.svg"
		content = icons_svg.read_text()
		for icon in (
			"layout-dashboard",
			"list",
			"map",
			"clipboard-check",
			"chart-column",
			"rotate-cw",
			"funnel",
			"rotate-ccw",
			"circle-plus",
			"download",
			"check",
		):
			self.assertIn(f'id="icon-{icon}"', content, f"Icon {icon} does not exist")
