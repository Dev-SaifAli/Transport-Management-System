"""Tests for AL RANA desk metadata parity.

Covers the two customizations that used to live only in the localhost
database and are now reproducible from source control:

* the Transport Job list view column set, and
* the "TRN Number" label on ``Company.tax_id``.
"""

import json
import unittest
from pathlib import Path

import frappe

from transport_management.patches.setup_al_rana_desk_metadata_parity import (
	COMPANY_TAX_ID_FIELD,
	COMPANY_TAX_ID_LABEL,
	TRANSPORT_JOB,
	TRANSPORT_JOB_LIST_VIEW_FIELDS,
	execute,
)


APP_ROOT = Path(frappe.get_app_path("transport_management")).parent
TRANSPORT_JOB_PATH = (
	APP_ROOT
	/ "transport_management"
	/ "transport_management"
	/ "doctype"
	/ "transport_job"
	/ "transport_job.json"
)

# The column set the localhost blueprint actually renders.
EXPECTED_LIST_VIEW_COLUMNS = {
	"customer",
	"loading_site",
	"unloading_site",
	"material",
	"requested_quantity",
	"billing_status",
	"toll_billing_status",
}


class TestDeskMetadataParity(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("desk_metadata_parity")

	def tearDown(self):
		frappe.set_user("Administrator")
		try:
			frappe.db.rollback(save_point="desk_metadata_parity")
		except Exception:
			# A framework commit inside a test can release the savepoint; the
			# metadata state these tests assert is the intended end state, so
			# continuing is safe.
			pass

	def load_transport_job(self):
		return json.loads(TRANSPORT_JOB_PATH.read_text())

	def list_view_columns_from_json(self):
		job = self.load_transport_job()
		return {
			field["fieldname"]
			for field in job["fields"]
			if field.get("in_list_view") and field.get("fieldtype") != "Tab Break"
		}

	def test_json_declares_expected_list_view_columns(self):
		self.assertEqual(
			self.list_view_columns_from_json(),
			EXPECTED_LIST_VIEW_COLUMNS,
		)

	def test_sale_order_reference_is_hidden_in_list_view(self):
		"""The localhost UI suppressed this column via a Property Setter."""
		job = self.load_transport_job()
		field = {f["fieldname"]: f for f in job["fields"]}["sale_order_reference"]
		self.assertFalse(field.get("in_list_view"))

	def test_every_known_list_view_field_is_listed(self):
		"""Guards against a field being dropped from the reconciliation list."""
		job = self.load_transport_job()
		json_list_view = {
			field["fieldname"]
			for field in job["fields"]
			if field.get("in_list_view") and field.get("fieldtype") != "Tab Break"
		}
		self.assertTrue(
			set(TRANSPORT_JOB_LIST_VIEW_FIELDS).issuperset(json_list_view),
			f"unknown list-view fields: {json_list_view - set(TRANSPORT_JOB_LIST_VIEW_FIELDS)}",
		)

	def test_patch_is_idempotent(self):
		self.assertEqual(execute(), "AL RANA desk metadata reconciled with source")
		self.assertEqual(execute(), "AL RANA desk metadata reconciled with source")
		self.assertEqual(
			frappe.db.count("Property Setter", {"doc_type": TRANSPORT_JOB, "property": "in_list_view"}),
			0,
		)

	def test_patch_removes_only_in_list_view_setters(self):
		execute()
		remaining = frappe.get_all(
			"Property Setter",
			filters={"doc_type": TRANSPORT_JOB},
			pluck="property",
		)
		self.assertNotIn("in_list_view", remaining)

	def test_effective_metadata_matches_json(self):
		from frappe.modules import reload_doc

		reload_doc("transport_management", "doctype", "transport_job", force=True)
		execute()
		effective = {f.fieldname for f in frappe.get_meta(TRANSPORT_JOB).fields if f.in_list_view}
		self.assertEqual(effective, EXPECTED_LIST_VIEW_COLUMNS)

	def test_company_tax_id_label_applied(self):
		execute()
		# The label is delivered by a Property Setter, so assert on the
		# effective metadata rather than the raw DocField column.
		label = frappe.get_meta("Company").get_field(COMPANY_TAX_ID_FIELD).label
		self.assertEqual(label, COMPANY_TAX_ID_LABEL)

	def test_company_tax_id_label_uses_a_property_setter(self):
		execute()
		setter = frappe.db.get_value(
			"Property Setter",
			{"doc_type": "Company", "field_name": COMPANY_TAX_ID_FIELD, "property": "label"},
			["name", "value", "property_type"],
			as_dict=True,
		)
		self.assertEqual(setter.value, COMPANY_TAX_ID_LABEL)
		self.assertEqual(setter.property_type, "Data")

	def test_company_tax_id_label_survives_repeated_runs(self):
		execute()
		execute()
		count = frappe.db.count(
			"Property Setter",
			{"doc_type": "Company", "field_name": COMPANY_TAX_ID_FIELD, "property": "label"},
		)
		self.assertEqual(count, 1, "the label patch must not create duplicates")

	def test_company_tax_id_values_untouched(self):
		"""The label changes; stored tax identification values must not."""
		before = {
			company.name: company.tax_id
			for company in frappe.get_all("Company", fields=["name", "tax_id"], limit=0)
		}
		execute()
		after = {
			company.name: company.tax_id
			for company in frappe.get_all("Company", fields=["name", "tax_id"], limit=0)
		}
		self.assertEqual(before, after)

	def test_company_fieldtype_unchanged(self):
		execute()
		fieldtype = frappe.db.get_value(
			"DocField", {"parent": "Company", "fieldname": COMPANY_TAX_ID_FIELD}, "fieldtype"
		)
		self.assertEqual(fieldtype, "Data")

	def test_patch_returns_reconciliation_message(self):
		self.assertEqual(execute(), "AL RANA desk metadata reconciled with source")
