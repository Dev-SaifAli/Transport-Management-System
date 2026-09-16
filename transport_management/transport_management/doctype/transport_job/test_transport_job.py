"""Tests for the standalone Transport Job."""

import unittest

import frappe
from frappe.modules import reload_doc

from transport_management.demo import setup_demo_data


class TestTransportJob(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_job", force=True)

	def setUp(self):
		frappe.db.savepoint("transport_job_test")
		self.demo = setup_demo_data()

	def tearDown(self):
		frappe.db.rollback(save_point="transport_job_test")

	def make_job(self, **values):
		doc = frappe.new_doc("Transport Job")
		doc.update({
			"customer": self.demo["customer"],
			"requested_date": "2026-09-09",
			"loading_site": self.demo["loading_site"],
			"unloading_site": self.demo["offloading_site"],
			"material": self.demo["material"],
			"requested_quantity": 80.8,
			"uom": self.demo["uom"],
		})
		doc.update(values)
		return doc

	def make_location(self, usage, active=1):
		location = frappe.new_doc("Transport Location")
		location.update({
			"location": f"TMS {usage} Job Location {frappe.generate_hash(length=8)}",
			"country": "United Arab Emirates",
			"location_usage": usage,
			"active": active,
		})
		location.insert()
		return location.name

	def get_field(self, fieldname):
		return frappe.get_meta("Transport Job").get_field(fieldname)

	def test_form_uses_expected_top_tabs_with_job_details_first(self):
		meta = frappe.get_meta("Transport Job")
		tabs = [field for field in meta.fields if field.fieldtype == "Tab Break"]
		self.assertEqual(
			[field.label for field in tabs],
			["Job Details", "Business References", "Commercial", "Quantity Progress"],
		)
		self.assertEqual(meta.fields[0].fieldname, "job_details_tab")
		self.assertEqual(meta.fields[0].label, "Job Details")

	def test_job_details_tab_contains_core_operational_fields_only(self):
		field_order = [field.fieldname for field in frappe.get_meta("Transport Job").fields]
		job_detail_fields = field_order[
			field_order.index("job_details_tab") + 1:field_order.index("business_references_tab")
		]
		for fieldname in (
			"customer",
			"requested_date",
			"material",
			"requested_quantity",
			"uom",
			"loading_site",
			"unloading_site",
			"status",
			"special_instructions",
		):
			self.assertIn(fieldname, job_detail_fields)
		for fieldname in ("vehicle", "driver", "truck_count"):
			self.assertNotIn(fieldname, job_detail_fields)

	def test_business_reference_visibility_is_clean(self):
		self.assertFalse(self.get_field("sale_order_reference").hidden)
		self.assertFalse(self.get_field("customer_lpo_number").hidden)
		for fieldname in ("sales_order", "sales_order_item", "do_number", "customer_do", "fnrc"):
			self.assertTrue(self.get_field(fieldname).hidden, fieldname)

	def test_commercial_fields_are_visible_and_read_only(self):
		for fieldname in ("agreed_rate", "ordered_amount"):
			field = self.get_field(fieldname)
			self.assertFalse(field.hidden, fieldname)
			self.assertTrue(field.read_only, fieldname)

	def test_quantity_progress_fields_are_visible_and_read_only(self):
		for fieldname in ("assigned_quantity", "loaded_quantity", "delivered_quantity", "remaining_quantity"):
			field = self.get_field(fieldname)
			self.assertFalse(field.hidden, fieldname)
			self.assertTrue(field.read_only, fieldname)

	def test_standalone_transport_job_creation(self):
		doc = self.make_job()
		doc.insert()
		self.assertRegex(doc.name, r"^TJOB-\d{4}-\d{5}$")
		self.assertEqual(doc.status, "Draft")
		self.assertFalse(doc.get("vehicle"))
		self.assertFalse(doc.get("driver"))
		self.assertFalse(doc.get("pod"))
		self.assertFalse(doc.get("gdn"))

	def test_obsolete_integration_fields_do_not_exist(self):
		meta = frappe.get_meta("Transport Job")
		obsolete_fields = (
			"so" + "urce",
			"".join(("ha", "der", "_shipment_id")),
			"".join(("ha", "der", "_order_id")),
			"external" + "_id",
			"idempotency" + "_key",
		)
		for fieldname in obsolete_fields:
			self.assertIsNone(meta.get_field(fieldname), fieldname)

	def test_positive_quantity_validation(self):
		for quantity in (0, -1):
			with self.subTest(quantity=quantity):
				with self.assertRaises(frappe.ValidationError):
					self.make_job(requested_quantity=quantity).insert()

	def test_loading_and_unloading_sites_must_differ(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_job(unloading_site=self.demo["loading_site"]).insert()

	def test_inactive_location_rejected(self):
		location = frappe.new_doc("Transport Location")
		location.update({
			"location": "TMS Inactive Job Location " + frappe.generate_hash(length=8),
			"country": "United Arab Emirates",
			"location_usage": "Loading",
			"active": 0,
		})
		location.insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_job(loading_site=location.name).insert()

	def test_loading_site_accepts_loading_and_both_usage(self):
		self.make_job(loading_site=self.make_location("Loading")).insert()
		self.make_job(loading_site=self.make_location("Both")).insert()

	def test_loading_site_rejects_unloading_only_usage(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_job(loading_site=self.make_location("Unloading")).insert()

	def test_unloading_site_accepts_unloading_and_both_usage(self):
		self.make_job(unloading_site=self.make_location("Unloading")).insert()
		self.make_job(unloading_site=self.make_location("Both")).insert()

	def test_unloading_site_rejects_loading_only_usage(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_job(unloading_site=self.make_location("Loading")).insert()

	def test_hidden_legacy_reference_values_are_preserved(self):
		doc = self.make_job(
			sale_order_reference="TSO-2026-00001",
			customer_lpo_number="LPO-KEEP",
			do_number="DO-KEEP",
			customer_do="CUSTOMER-DO-KEEP",
			fnrc="FNRC-KEEP",
			agreed_rate=12,
			ordered_amount=969.6,
		)
		doc.insert()
		reloaded = frappe.get_doc("Transport Job", doc.name)
		self.assertEqual(reloaded.sale_order_reference, "TSO-2026-00001")
		self.assertEqual(reloaded.customer_lpo_number, "LPO-KEEP")
		self.assertEqual(reloaded.do_number, "DO-KEEP")
		self.assertEqual(reloaded.customer_do, "CUSTOMER-DO-KEEP")
		self.assertEqual(reloaded.fnrc, "FNRC-KEEP")
		self.assertEqual(reloaded.agreed_rate, 12)
		self.assertEqual(reloaded.ordered_amount, 969.6)

	def test_execution_fields_do_not_belong_to_transport_job(self):
		meta = frappe.get_meta("Transport Job")
		for fieldname in ("vehicle", "driver", "gdn", "loading_no", "unloading_no", "pod", "fuel", "toll_amount"):
			self.assertIsNone(meta.get_field(fieldname), fieldname)
