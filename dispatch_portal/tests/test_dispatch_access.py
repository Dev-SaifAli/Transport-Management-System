"""Server-side access control for the AL RANA Dispatch console."""

import frappe

from dispatch_portal.services.dispatch_access import (
	CONSOLE_READ_ROLES,
	DISPATCH_DOCTYPES,
	ROLE_DISPATCHER,
	ROLE_VERIFIER,
	VERIFICATION_ROLES,
	is_verifier,
	require_console_access,
	require_verification_access,
)
from dispatch_portal.tests.test_helpers import DispatchTestCase, make_user


class TestDispatchAccessControl(DispatchTestCase):
	def setUp(self):
		super().setUp()
		self.manager = make_user(["Transport Manager"], "Dispatch Manager")
		self.dispatcher_only = make_user([ROLE_DISPATCHER], "Console Dispatcher")
		self.verifier_only = make_user([ROLE_VERIFIER], "Document Verifier")
		self.entry_user = make_user(["TMS Trip Data Entry"], "Trip Entry")
		self.outsider = make_user(["Website Manager"], "No Dispatch Access")

	def test_administrator_has_full_access(self):
		frappe.set_user("Administrator")
		self.assertTrue(is_verifier())
		require_console_access()
		require_verification_access()

	def test_transport_manager_can_use_the_console_and_verify(self):
		frappe.set_user(self.manager)
		require_console_access()
		require_verification_access()
		self.assertTrue(is_verifier())

	def test_legacy_trip_data_entry_role_keeps_console_access(self):
		frappe.set_user(self.entry_user)
		require_console_access()
		self.assertFalse(is_verifier())

	def test_dispatch_only_role_gets_read_only_access(self):
		frappe.set_user(self.dispatcher_only)
		require_console_access()
		self.assertFalse(is_verifier())
		self.assertRaises(frappe.PermissionError, require_verification_access)

	def test_verifier_only_role_cannot_verify_documents(self):
		"""Verification requires the whole console access plus the verifier role."""
		frappe.set_user(self.verifier_only)
		require_console_access()
		require_verification_access()

	def test_unrelated_user_is_rejected(self):
		frappe.set_user(self.outsider)
		self.assertFalse(is_verifier())
		self.assertRaises(frappe.PermissionError, require_console_access)

	def test_guest_is_rejected(self):
		frappe.set_user("Guest")
		self.assertFalse(is_verifier())
		self.assertRaises(frappe.PermissionError, require_console_access)

	def test_verification_roles_are_narrower_than_console_roles(self):
		self.assertTrue(VERIFICATION_ROLES.issubset(CONSOLE_READ_ROLES))
		self.assertIn(ROLE_VERIFIER, VERIFICATION_ROLES)
		self.assertNotIn("TMS Trip Data Entry", VERIFICATION_ROLES)

	def test_doctype_read_helper_rejects_non_console_doctypes(self):
		frappe.set_user("Administrator")
		from dispatch_portal.services.dispatch_access import require_doctype_read

		require_doctype_read("Transport Trip")
		self.assertRaises(frappe.ValidationError, require_doctype_read, "User")

	def test_doctype_read_helper_enforces_frappe_permissions(self):
		frappe.set_user(self.outsider)
		from dispatch_portal.services.dispatch_access import require_doctype_read

		self.assertRaises(frappe.PermissionError, require_doctype_read, "Transport Trip")

	def test_exposed_doctypes_are_tms_entities_only(self):
		for doctype in ("Transport Trip", "Transport Job", "Truck", "Truck Driver"):
			self.assertIn(doctype, DISPATCH_DOCTYPES)
		for forbidden in ("Page", "User", "Role", "DocType", "File"):
			self.assertNotIn(forbidden, DISPATCH_DOCTYPES)

	def test_role_flags_for_dispatcher_only_user(self):
		frappe.set_user(self.dispatcher_only)
		from dispatch_portal.services.dispatch_access import get_dispatch_roles_for_user

		flags = get_dispatch_roles_for_user()
		self.assertTrue(flags["is_dispatcher"])
		self.assertFalse(flags["is_verifier"])
		self.assertIn(ROLE_DISPATCHER, flags["roles"])

	def test_role_flags_for_guest(self):
		frappe.set_user("Guest")
		from dispatch_portal.services.dispatch_access import get_dispatch_roles_for_user

		flags = get_dispatch_roles_for_user()
		self.assertFalse(flags["is_dispatcher"])
		self.assertFalse(flags["is_verifier"])


class TestConsoleBootApi(DispatchTestCase):
	def test_boot_lists_all_five_sections_for_a_verifier(self):
		frappe.set_user(make_user(["Transport Manager"], "Boot Manager"))
		from dispatch_portal.api.permissions import get_console_boot

		boot = get_console_boot()
		keys = [row["key"] for row in boot["sections"]]
		self.assertEqual(
			keys,
			["dashboard", "trips", "trip-map", "verification", "reports"],
		)
		self.assertEqual(boot["route"], "/app/dispatch-console")
		self.assertEqual(boot["section"], "dashboard")

	def test_boot_hides_verification_for_non_verifier(self):
		frappe.set_user(make_user([ROLE_DISPATCHER], "Boot Dispatcher"))
		from dispatch_portal.api.permissions import get_console_boot

		keys = [row["key"] for row in get_console_boot()["sections"]]
		self.assertNotIn("verification", keys)
		self.assertIn("trips", keys)

	def test_boot_denies_unrelated_user(self):
		frappe.set_user(make_user(["Website Manager"], "Boot Outsider"))
		from dispatch_portal.api.permissions import get_console_boot

		self.assertRaises(frappe.PermissionError, get_console_boot)

	def test_has_console_access_probe(self):
		frappe.set_user(make_user([ROLE_DISPATCHER], "Probe User"))
		from dispatch_portal.api.permissions import has_console_access

		result = has_console_access()
		self.assertTrue(result["has_access"])
		self.assertFalse(result["is_verifier"])
