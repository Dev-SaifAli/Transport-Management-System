import unittest

import frappe

from transport_management.party_master import ensure_supplier_transport_fields


class TestHiredVehicle(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("hired_vehicle_test")
		ensure_supplier_transport_fields()

	def tearDown(self):
		frappe.db.rollback(save_point="hired_vehicle_test")

	def make_supplier(self, **values):
		doc = frappe.new_doc("Supplier")
		doc.update({
			"supplier_name": "TMS Hired Vehicle Supplier " + frappe.generate_hash(length=8),
			"supplier_type": "Company",
			"is_transporter": 1,
			"transporter_status": "Active",
		})
		doc.update(values)
		doc.insert()
		return doc

	def make_hired_vehicle(self, supplier=None, **values):
		if supplier is None:
			supplier = self.make_supplier()
		doc = frappe.new_doc("Hired Vehicle")
		doc.update({
			"transporter": supplier.name,
			"plate_number": "HV-" + frappe.generate_hash(length=8),
		})
		doc.update(values)
		return doc

	def test_valid_hired_vehicle_creation(self):
		vehicle = self.make_hired_vehicle()
		vehicle.insert()
		self.assertEqual(vehicle.active, 1)
		self.assertTrue(vehicle.transporter)
		self.assertTrue(vehicle.plate_number)

	def test_non_transporter_supplier_rejected(self):
		supplier = self.make_supplier(is_transporter=0)
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_vehicle(supplier=supplier).insert()

	def test_disabled_supplier_rejected(self):
		supplier = self.make_supplier(disabled=1)
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_vehicle(supplier=supplier).insert()

	def test_duplicate_plate_for_same_transporter_rejected(self):
		supplier = self.make_supplier()
		self.make_hired_vehicle(supplier=supplier, plate_number="DUP-HV-001").insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_vehicle(supplier=supplier, plate_number="DUP-HV-001").insert()
