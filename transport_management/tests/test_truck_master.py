"""Tests for the owned Truck master extension."""

import unittest

import frappe

from transport_management.demo import setup_demo_data
from transport_management.truck_master import ensure_owned_truck_fields


class TestOwnedTruckMaster(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("owned_truck_master_test")
		ensure_owned_truck_fields()
		self.demo = setup_demo_data()
		self.job = frappe.get_doc("Transport Job", self.demo["transport_job"])
		frappe.db.delete("Transport Trip", {"transport_job": self.job.name})

	def tearDown(self):
		frappe.db.rollback(save_point="owned_truck_master_test")

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

	def make_truck(self, **values):
		fuel_uom = self.demo["fuel_uom"]
		doc = frappe.new_doc("Truck")
		hash_value = frappe.generate_hash(length=8)
		doc.update({
			"truck_number": "TMS-OWN-" + hash_value,
			"license_plate": "TMS-OWN-" + hash_value,
			"make": "Test Make",
			"model": "Test Model",
			"manufacturing_year": "2026",
			"acquisition_date": 2026,
			"fuel_type": "Diesel",
			"fuel_uom": fuel_uom,
			"chassis_number": "CHS-" + hash_value,
			"status": "Idle",
			"disabled": 0,
			"ownership_type": "OWN",
		})
		doc.update(values)
		doc.insert()
		return doc

	def test_truck_field_installer_is_idempotent(self):
		before = frappe.db.count("Custom Field", {"dt": "Truck"})
		ensure_owned_truck_fields()
		ensure_owned_truck_fields()
		after = frappe.db.count("Custom Field", {"dt": "Truck"})
		self.assertEqual(before, after)

	def test_custom_truck_fields_exist(self):
		meta = frappe.get_meta("Truck")
		self.assertEqual(meta.get_field("vehicle_type").options, "Truck Type")
		self.assertEqual(meta.get_field("capacity").fieldtype, "Float")
		self.assertEqual(meta.get_field("capacity_uom").options, "UOM")
		self.assertEqual(meta.get_field("ownership_type").options, "OWN")
		self.assertEqual(meta.get_field("ownership_type").default, "OWN")
		self.assertEqual(meta.get_field("erpnext_asset").options, "Asset")

	def test_existing_truck_defaults_to_owned(self):
		frappe.db.set_value("Truck", self.demo["vehicle"], "ownership_type", None)
		ensure_owned_truck_fields()
		self.assertEqual(frappe.db.get_value("Truck", self.demo["vehicle"], "ownership_type"), "OWN")

	def test_create_active_owned_truck(self):
		truck = self.make_truck(capacity=30, capacity_uom=self.demo["uom"])
		self.assertEqual(truck.ownership_type, "OWN")
		self.assertEqual(truck.status, "Idle")
		self.assertFalse(truck.disabled)

	def test_valid_enabled_idle_truck_accepted_for_own_trip(self):
		trip = self.make_trip()
		trip.insert()
		self.assertEqual(trip.vehicle, self.demo["vehicle"])

	def test_disabled_truck_rejected_for_own_trip(self):
		frappe.db.set_value("Truck", self.demo["vehicle"], "disabled", 1)
		with self.assertRaises(frappe.ValidationError):
			self.make_trip().insert()

	def test_non_idle_truck_rejected_for_own_trip(self):
		for status in ("Under Maintenance", "On Trip", "Disabled"):
			with self.subTest(status=status):
				frappe.db.set_value("Truck", self.demo["vehicle"], {"status": status, "disabled": 0})
				with self.assertRaises(frappe.ValidationError):
					self.make_trip().insert()
				frappe.db.set_value("Truck", self.demo["vehicle"], "status", "Idle")

	def test_trip_driver_can_differ_from_truck_default_driver(self):
		frappe.db.set_value("Truck", self.demo["vehicle"], "trans_ms_driver", None)
		trip = self.make_trip()
		trip.insert()
		self.assertEqual(trip.driver, self.demo["driver"])

	def test_optional_asset_link_field_targets_erpnext_asset(self):
		field = frappe.get_meta("Truck").get_field("erpnext_asset")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Asset")
