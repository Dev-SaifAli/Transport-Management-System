"""Tests for the Transport Location master extension."""

import unittest

import frappe

from transport_management.demo import setup_demo_data
from transport_management.location_master import ensure_transport_location_fields


class TestLocationMaster(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("location_master_test")
		ensure_transport_location_fields()
		self.demo = setup_demo_data()
		self.job = frappe.get_doc("Transport Job", self.demo["transport_job"])
		frappe.db.set_value("Truck", self.demo["vehicle"], "vehicle_type", "TIPPER")
		frappe.db.set_value("Transport Job", self.job.name, "material", "3/4 AGREEGAT(10MM-20MM)")
		self.job.reload()

	def tearDown(self):
		frappe.db.rollback(save_point="location_master_test")

	def make_location(self, **values):
		doc = frappe.new_doc("Transport Location")
		doc.update({
			"location": "TMS Test Location " + frappe.generate_hash(length=8),
			"country": "United Arab Emirates",
			"location_type": "Other",
			"location_usage": "Both",
			"active": 1,
		})
		doc.update(values)
		doc.insert()
		return doc

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

	def make_trip(self, **values):
		doc = frappe.new_doc("Transport Trip")
		doc.update({
			"transport_job": self.job.name,
			"execution_source": "OWN",
			"trip_date": self.job.requested_date,
			"vehicle": self.demo["vehicle"],
			"driver": self.demo["driver"],
			"loading_site": self.job.loading_site,
			"unloading_site": self.job.unloading_site,
			"material": self.job.material,
			"planned_quantity": 1,
			"uom": self.job.uom,
		})
		doc.update(values)
		return doc

	def test_active_location_creation(self):
		location = self.make_location(location_type="Yard", location_usage="Both", city="Sharjah")
		self.assertEqual(location.location_type, "Yard")
		self.assertEqual(location.location_usage, "Both")
		self.assertEqual(location.city, "Sharjah")
		self.assertTrue(location.active)

	def test_valid_active_job_locations(self):
		loading = self.make_location(location_type="Plant", location_usage="Loading")
		unloading = self.make_location(
			location_type="Customer Site",
			location_usage="Unloading",
			customer=self.demo["customer"],
		)
		job = self.make_job(loading_site=loading.name, unloading_site=unloading.name)
		job.insert()
		self.assertEqual(job.loading_site, loading.name)
		self.assertEqual(job.unloading_site, unloading.name)

	def test_same_loading_and_unloading_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_job(unloading_site=self.demo["loading_site"]).insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(unloading_site=self.job.loading_site).insert()

	def test_inactive_job_location_rejected(self):
		inactive = self.make_location(active=0)
		with self.assertRaises(frappe.ValidationError):
			self.make_job(loading_site=inactive.name).insert()

	def test_inactive_trip_location_rejected(self):
		inactive = self.make_location(active=0)
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(loading_site=inactive.name).insert()

	def test_trip_defaults_locations_from_job(self):
		from transport_management.transport_management.doctype.transport_trip.transport_trip import (
			get_defaults_from_transport_job,
		)

		defaults = get_defaults_from_transport_job(self.job.name)
		self.assertEqual(defaults["loading_site"], self.job.loading_site)
		self.assertEqual(defaults["unloading_site"], self.job.unloading_site)

	def test_location_installer_is_idempotent(self):
		before = frappe.db.count("Custom Field", {"dt": "Transport Location"})
		ensure_transport_location_fields()
		ensure_transport_location_fields()
		after = frappe.db.count("Custom Field", {"dt": "Transport Location"})
		self.assertEqual(before, after)

	def test_transport_location_is_owned_by_transport_management(self):
		self.assertEqual(frappe.db.get_value("DocType", "Transport Location", "module"), "Transport Management")
		self.assertEqual(
			frappe.db.get_value("Module Def", "Transport Management", "app_name"),
			"transport_management",
		)
		self.assertEqual(frappe.db.count("DocType", {"name": "Transport Location"}), 1)

	def test_transport_location_table_and_records_are_preserved(self):
		self.assertTrue(frappe.db.table_exists("Transport Location"))
		self.assertGreaterEqual(frappe.db.count("Transport Location"), 2)
		self.assertTrue(frappe.db.exists("Transport Location", "ATBT AL TAWEEN"))
		self.assertTrue(frappe.db.exists("Transport Location", "SAJJA ORYX"))

	def test_location_field_remains_unique(self):
		field = frappe.get_meta("Transport Location").get_field("location")
		self.assertTrue(field.unique)

	def test_location_fields_are_standard_after_ownership_migration(self):
		standard_fields = {
			row.fieldname
			for row in frappe.get_all("DocField", filters={"parent": "Transport Location"}, fields=["fieldname"])
		}
		for fieldname in (
			"location_type",
			"location_usage",
			"customer",
			"supplier",
			"address",
			"city",
			"latitude",
			"longitude",
			"active",
			"notes",
		):
			self.assertIn(fieldname, standard_fields)
			self.assertFalse(
				frappe.db.exists("Custom Field", {"dt": "Transport Location", "fieldname": fieldname})
			)
		self.assertEqual(
			frappe.db.get_value("Transport Location", "ATBT AL TAWEEN", "location_type"),
			"Plant",
		)
		self.assertEqual(
			frappe.db.get_value("Transport Location", "ATBT AL TAWEEN", "location_usage"),
			"Loading",
		)
		self.assertEqual(
			frappe.db.get_value("Transport Location", "SAJJA ORYX", "location_usage"),
			"Unloading",
		)
		self.assertEqual(
			frappe.db.get_value("Transport Location", "SAJJA ORYX", "customer"),
			self.demo["customer"],
		)

	def test_existing_job_and_trip_location_links_resolve(self):
		self.assertTrue(frappe.db.exists("Transport Location", self.job.loading_site))
		self.assertTrue(frappe.db.exists("Transport Location", self.job.unloading_site))
		for trip_name in self.demo["transport_trips"]:
			trip = frappe.get_doc("Transport Trip", trip_name)
			self.assertTrue(frappe.db.exists("Transport Location", trip.loading_site))
			self.assertTrue(frappe.db.exists("Transport Location", trip.unloading_site))
