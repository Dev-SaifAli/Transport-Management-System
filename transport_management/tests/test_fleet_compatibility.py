"""Site tests: no generated Fleet fixtures, Trips, or permanent business records."""

import unittest
from copy import deepcopy
from unittest.mock import patch

import frappe

from transport_management.fleet_compatibility import ensure_assignment_table


class TestFleetCompatibility(unittest.TestCase):
	def test_metadata_and_idempotence(self):
		field = frappe.get_meta("Transportation Order").get_field("assign_transport")
		self.assertIsNotNone(field)
		self.assertEqual((field.fieldtype, field.options), ("Table", "Transport Assignments"))
		before = frappe.db.count("Custom Field", {"dt": "Transportation Order", "fieldname": "assign_transport"})
		ensure_assignment_table()
		ensure_assignment_table()
		self.assertEqual(before, frappe.db.count("Custom Field", {"dt": "Transportation Order", "fieldname": "assign_transport"}))

	def test_conflicting_field_is_not_overwritten(self):
		meta = deepcopy(frappe.get_meta("Transportation Order", cached=False))
		meta.get_field("assign_transport").options = "Cargo Detail"
		child = frappe.get_meta("Transport Assignments")
		with patch("transport_management.fleet_compatibility.frappe.get_meta", side_effect=[meta, child]):
			with patch("transport_management.fleet_compatibility.create_custom_field") as create:
				with self.assertRaises(frappe.ValidationError):
					ensure_assignment_table()
				create.assert_not_called()

	def test_minimal_order_insert_and_reload(self):
		frappe.db.savepoint("tms_order_test")
		try:
			doc = frappe.new_doc("Transportation Order")
			doc.date = frappe.utils.today()
			doc.cargo_type = "Loose Cargo"
			doc.amount = 80.8
			doc.validate()  # This exact path previously raised AttributeError.
			doc.insert()
			doc = frappe.get_doc("Transportation Order", doc.name)
			self.assertEqual(doc.assign_transport, [])
			self.assertEqual(doc.assignment_status, "Waiting Assignment")
			doc.save()
		finally:
			frappe.db.rollback(save_point="tms_order_test")

	def test_fleet_currency_and_quantity_calculation_are_preserved(self):
		doc = frappe.new_doc("Transportation Order")
		doc.customer = "Test customer (not persisted)"
		doc.cargo_type = "Loose Cargo"
		doc.amount = 80.8
		row = doc.append("assign_transport", {"amount": 40.4})
		with patch("vsd_fleet_ms.vsd_fleet_ms.doctype.transportation_order.transportation_order.frappe.get_value", return_value="AED"):
			doc.validate()
		self.assertEqual(row.currency, "AED")
		doc.before_save()
		self.assertEqual(doc.assignment_status, "Partially Assigned")
		row.amount = 80.8
		doc.before_save()
		self.assertEqual(doc.assignment_status, "Fully Assigned")

	def test_existing_fleet_vehicle_guard_still_raises(self):
		doc = frappe.new_doc("Transportation Order")
		doc.append("assign_transport", {"assigned_vehicle": "Test truck (not persisted)"})
		# Fleet currently checks 'In Trip', although Truck offers 'On Trip'.
		# Preserve and test the existing branch, without changing upstream rules.
		with patch("vsd_fleet_ms.vsd_fleet_ms.doctype.transportation_order.transportation_order.frappe.get_value", return_value="In Trip"):
			with patch("vsd_fleet_ms.vsd_fleet_ms.doctype.transportation_order.transportation_order.frappe.db.get_value", return_value=None):
				with self.assertRaises(frappe.ValidationError):
					doc.validate()
