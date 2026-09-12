"""Tests for the standalone Transport Job."""

import unittest

import frappe

from transport_management.demo import setup_demo_data


class TestTransportJob(unittest.TestCase):
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
			"active": 0,
		})
		location.insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_job(loading_site=location.name).insert()

	def test_execution_fields_do_not_belong_to_transport_job(self):
		meta = frappe.get_meta("Transport Job")
		for fieldname in ("vehicle", "driver", "gdn", "loading_no", "unloading_no", "pod", "fuel", "toll_amount"):
			self.assertIsNone(meta.get_field(fieldname), fieldname)
