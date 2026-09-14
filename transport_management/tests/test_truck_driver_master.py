"""Tests for Truck Driver ownership and Employee relationship."""

import unittest

import frappe
from frappe.model.base_document import get_controller

from transport_management.demo import setup_demo_data


class TestTruckDriverMaster(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("truck_driver_master_test")
		self.demo = setup_demo_data()
		self.driver = frappe.get_doc("Truck Driver", self.demo["driver"])

	def tearDown(self):
		frappe.db.rollback(save_point="truck_driver_master_test")

	def test_truck_driver_is_owned_by_transport_management(self):
		self.assertEqual(frappe.db.get_value("DocType", "Truck Driver", "module"), "Transport Management")
		self.assertEqual(
			frappe.db.get_value("Module Def", "Transport Management", "app_name"),
			"transport_management",
		)
		self.assertEqual(frappe.db.count("DocType", {"name": "Truck Driver"}), 1)

	def test_truck_driver_table_and_existing_record_are_preserved(self):
		self.assertTrue(frappe.db.table_exists("Truck Driver"))
		self.assertTrue(frappe.db.exists("Truck Driver", "Driver-2026-0001"))
		self.assertGreaterEqual(frappe.db.count("Truck Driver"), 1)

	def test_truck_driver_naming_behavior_is_preserved(self):
		meta = frappe.get_meta("Truck Driver")
		self.assertEqual(meta.autoname, "format:Driver-{YYYY}-{####}")
		self.assertEqual(meta.title_field, "full_name")
		self.assertEqual(meta.search_fields, "full_name")

	def test_transport_trip_driver_still_links_to_truck_driver(self):
		field = frappe.get_meta("Transport Trip").get_field("driver")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Truck Driver")
		for trip_name in self.demo["transport_trips"]:
			trip = frappe.get_doc("Transport Trip", trip_name)
			self.assertTrue(frappe.db.exists("Truck Driver", trip.driver))

	def test_truck_default_driver_still_links_to_truck_driver(self):
		field = frappe.get_meta("Truck").get_field("trans_ms_driver")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Truck Driver")

	def test_inactive_driver_clears_truck_default_driver(self):
		truck = frappe.get_doc("Truck", self.demo["vehicle"])
		truck.trans_ms_driver = self.driver.name
		truck.trans_ms__driver_name = self.driver.full_name
		truck.save()

		self.driver.status = "Suspended"
		self.driver.save()

		self.assertFalse(frappe.db.get_value("Truck", truck.name, "trans_ms_driver"))
		self.assertFalse(frappe.db.get_value("Truck", truck.name, "trans_ms__driver_name"))

	def test_employee_link_exists_once_and_is_optional(self):
		meta = frappe.get_meta("Truck Driver")
		employee_fields = [field for field in meta.fields if field.fieldname == "employee"]
		self.assertEqual(len(employee_fields), 1)
		self.assertEqual(employee_fields[0].fieldtype, "Link")
		self.assertEqual(employee_fields[0].options, "Employee")
		self.assertFalse(employee_fields[0].reqd)

	def test_truck_driver_no_longer_depends_on_fleet_document_child_table(self):
		meta = frappe.get_meta("Truck Driver")
		self.assertFalse(meta.get_field("drivers_document"))
		targets = {
			field.options
			for field in meta.fields
			if field.fieldtype in {"Link", "Table"} and field.options
		}
		self.assertNotIn("Document Attachments", targets)

	def test_existing_driver_saves_without_employee(self):
		self.driver.employee = None
		self.driver.save()
		self.assertFalse(self.driver.employee)

	def test_linked_employee_can_be_assigned_and_saved(self):
		employee = make_employee()
		self.driver.employee = employee.name
		self.driver.save()
		self.assertEqual(frappe.db.get_value("Truck Driver", self.driver.name, "employee"), employee.name)

	def test_hired_trip_still_does_not_require_truck_driver_or_employee(self):
		frappe.db.delete("Transport Trip", {"transport_job": self.demo["transport_job"]})

		trip = frappe.new_doc("Transport Trip")
		trip.update({
			"transport_job": self.demo["transport_job"],
			"execution_source": "HIRED",
			"trip_date": "2026-09-09",
			"transporter": self.demo["transporter_supplier"],
			"hired_vehicle": self.demo["hired_vehicle"],
			"loading_site": self.demo["loading_site"],
			"unloading_site": self.demo["offloading_site"],
			"material": self.demo["material"],
			"planned_quantity": 1,
			"uom": self.demo["uom"],
		})
		trip.insert()
		self.assertFalse(trip.driver)
		self.assertFalse(trip.hired_driver)

	def test_no_duplicate_truck_driver_metadata_exists(self):
		self.assertEqual(frappe.db.count("DocType", {"name": "Truck Driver"}), 1)

	def test_no_fleet_specific_truck_driver_controller_is_used(self):
		self.assertEqual(
			get_controller("Truck Driver").__module__,
			"transport_management.transport_management.doctype.truck_driver.truck_driver",
		)


class TestTruckDriverOwnershipMigration(unittest.TestCase):
	def test_ownership_migration_is_idempotent(self):
		from transport_management.truck_driver_master import migrate_truck_driver_ownership

		before = frappe.db.count("Truck Driver")
		migrate_truck_driver_ownership()
		migrate_truck_driver_ownership()
		self.assertEqual(frappe.db.count("Truck Driver"), before)
		self.assertEqual(frappe.db.get_value("DocType", "Truck Driver", "module"), "Transport Management")


def make_employee():
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		company = frappe.get_all("Company", pluck="name", limit=1)[0]

	employee = frappe.new_doc("Employee")
	employee.update({
		"first_name": "TMS Driver",
		"employee_name": "TMS Driver",
		"gender": get_or_create_gender(),
		"date_of_birth": "1990-01-01",
		"date_of_joining": "2026-01-01",
		"company": company,
	})
	employee.insert()
	return employee


def get_or_create_gender():
	gender = frappe.get_all("Gender", pluck="name", limit=1)
	if gender:
		return gender[0]
	doc = frappe.get_doc({"doctype": "Gender", "gender": "Other"})
	doc.insert()
	return doc.name
