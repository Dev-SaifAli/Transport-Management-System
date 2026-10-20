"""Dispatch website access checks without a site or database connection."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe

from dispatch_portal.services import dispatch_access
from dispatch_portal.www import dispatch


class TestDispatchWebsiteAccess(unittest.TestCase):
	def setUp(self):
		self.session = frappe._dict(user="Guest", data=frappe._dict())
		self.local = SimpleNamespace(flags=frappe._dict(), session=self.session)
		self.db = Mock()
		self.db.exists.return_value = True
		self.roles = Mock(return_value=[])
		self.csrf = Mock(return_value="test-csrf")
		self.full_name = Mock(return_value="Dispatch Test User")
		self.throw = Mock(side_effect=self.raise_permission_error)

		for patcher in (
			patch.object(frappe, "session", self.session),
			patch.object(frappe, "local", self.local),
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "get_roles", self.roles),
			patch.object(frappe, "throw", self.throw),
			patch.object(dispatch_access, "_", lambda message: message),
			patch.object(frappe.sessions, "get_csrf_token", self.csrf),
			patch.object(frappe.utils, "get_fullname", self.full_name),
		):
			patcher.start()
			self.addCleanup(patcher.stop)

	@staticmethod
	def raise_permission_error(message, exc):
		raise exc(message)

	def test_guest_keeps_login_redirect_without_building_portal_context(self):
		context = frappe._dict()
		with self.assertRaises(frappe.Redirect):
			dispatch.get_context(context)

		self.assertEqual(self.local.flags.redirect_location, "/login?redirect-to=/dispatch")
		self.assertEqual(context, {})
		self.db.exists.assert_not_called()
		self.roles.assert_not_called()
		self.throw.assert_not_called()
		self.csrf.assert_not_called()
		self.full_name.assert_not_called()

	def test_existing_console_roles_and_administrator_can_open_portal(self):
		for role in sorted(dispatch_access.CONSOLE_READ_ROLES):
			with self.subTest(role=role):
				self.session.user = "dispatcher@example.invalid"
				self.roles.return_value = [role]
				context = frappe._dict()

				self.assertIs(dispatch.get_context(context), context)
				self.assertEqual(context.no_cache, 1)
				self.assertEqual(json.loads(context.frappe_boot_json), {
					"csrf_token": "test-csrf",
					"user": self.session.user,
					"full_name": "Dispatch Test User",
				})
				self.roles.assert_called_with(self.session.user)

		self.session.user = "Administrator"
		self.roles.return_value = []
		self.assertEqual(dispatch.get_context(frappe._dict()).no_cache, 1)
		self.throw.assert_not_called()

	def test_authenticated_user_without_console_role_is_forbidden(self):
		self.session.user = "outsider@example.invalid"
		self.roles.return_value = ["Website Manager"]
		context = frappe._dict()

		with self.assertRaises(dispatch_access.DispatchAccessError) as raised:
			dispatch.get_context(context)

		self.assertIsInstance(raised.exception, frappe.PermissionError)
		self.assertEqual(raised.exception.http_status_code, 403)
		self.assertEqual(context, {})
		self.assertNotIn("redirect_location", self.local.flags)
		self.throw.assert_called_once()
		self.csrf.assert_not_called()
		self.full_name.assert_not_called()
