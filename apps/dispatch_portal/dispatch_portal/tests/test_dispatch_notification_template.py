"""Tests for the source-controlled Dispatch Notification email template.

The template used to exist only in the localhost database. It is now a
fixture so a fresh install reproduces it without duplicates.
"""

import json
import unittest
from pathlib import Path

import frappe

from dispatch_portal.hooks import fixtures


TEMPLATE_NAME = "Dispatch Notification"
EXPECTED_SUBJECT = "Your order is out for delivery!"

FIXTURE_TEMPLATE_FILTERS = [
	{
		"dt": "Email Template",
		"filters": [["name", "=", TEMPLATE_NAME]],
	}
]


class TestDispatchNotificationTemplate(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		frappe.db.savepoint("dispatch_notification_template")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback(save_point="dispatch_notification_template")

	def fixture_path(self):
		app_path = Path(frappe.get_app_path("dispatch_portal"))
		return app_path / "fixtures" / "email_template.json"

	def load_fixture(self):
		return json.loads(self.fixture_path().read_text())

	def test_fixture_file_exists(self):
		self.assertTrue(self.fixture_path().is_file(), "email_template.json fixture is missing")

	def test_fixture_holds_one_template(self):
		self.assertEqual(len(self.load_fixture()), 1)

	def test_fixture_doctype_and_name(self):
		doc = self.load_fixture()[0]
		self.assertEqual(doc["doctype"], "Email Template")
		self.assertEqual(doc["name"], TEMPLATE_NAME)

	def test_fixture_subject(self):
		self.assertEqual(self.load_fixture()[0]["subject"], EXPECTED_SUBJECT)

	def test_fixture_body_is_non_empty_and_references_delivery_fields(self):
		body = self.load_fixture()[0]["response"]
		self.assertTrue(body)
		for placeholder in ("{{ customer }}", "{{ delivery_note }}", "{{ driver_name }}"):
			self.assertIn(placeholder, body)

	def test_fixture_contains_no_environment_specific_values(self):
		"""No hosts, ports, credentials or site names may be committed."""
		doc = self.load_fixture()[0]
		text = json.dumps(doc).lower()
		for banned in ("railway", "localhost", "password", "secret", "api_key", "http://", "https://"):
			self.assertNotIn(banned, text)

	def test_hooks_declare_the_narrow_filter(self):
		self.assertEqual(fixtures, FIXTURE_TEMPLATE_FILTERS)

	def test_import_creates_no_duplicates(self):
		"""Importing the fixture twice must not duplicate the template."""
		from frappe.modules.import_file import import_doc

		docs = self.load_fixture()
		for _ in range(2):
			for doc in docs:
				import_doc(doc)

		self.assertEqual(frappe.db.count("Email Template", {"name": TEMPLATE_NAME}), 1)

	def test_template_subject_matches_fixture(self):
		actual = frappe.db.get_value("Email Template", TEMPLATE_NAME, "subject") if frappe.db.exists(
			"Email Template", TEMPLATE_NAME
		) else None
		if actual is not None:
			self.assertEqual(actual, EXPECTED_SUBJECT)
