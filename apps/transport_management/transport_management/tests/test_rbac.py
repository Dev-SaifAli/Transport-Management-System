"""Tests for TMS role profiles and DocType permissions."""

import unittest

import frappe

from transport_management.demo import setup_demo_data
from transport_management.imports import base_importer
from transport_management.rbac import (
	ROLE_TMS_EXPENSE_DATA_ENTRY,
	ROLE_TMS_TRIP_DATA_ENTRY,
	ROLE_TRANSPORT_ADMIN,
	ROLE_TRANSPORT_MANAGER,
	ensure_tms_rbac,
)


class TestTransportManagementRBAC(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		ensure_tms_rbac()

	def setUp(self):
		frappe.db.savepoint("tms_rbac_test")
		self.demo = setup_demo_data()
		self.trip_user = self.make_user("TMS Trip Data Entry")
		self.expense_user = self.make_user("TMS + Expense Data Entry")
		self.manager_user = self.make_user("Transport Manager")
		self.admin_user = self.make_user("Transport Admin")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="tms_rbac_test")

	def make_user(self, role_profile):
		email = f"{frappe.generate_hash(length=10).lower()}@tms-rbac.test"
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"enabled": 1,
			"first_name": role_profile,
			"new_password": "TMSRbac#2026",
			"role_profiles": [{"role_profile": role_profile}],
		})
		user.insert(ignore_permissions=True)
		frappe.clear_cache(user=email)
		return email

	def assert_can(self, user, doctype, ptype):
		self.assertTrue(
			frappe.has_permission(doctype, ptype=ptype, user=user),
			f"{user} should have {ptype} on {doctype}",
		)

	def assert_cannot(self, user, doctype, ptype):
		self.assertFalse(
			frappe.has_permission(doctype, ptype=ptype, user=user),
			f"{user} should not have {ptype} on {doctype}",
		)

	def test_roles_and_role_profiles_exist(self):
		for role in (
			ROLE_TMS_TRIP_DATA_ENTRY,
			ROLE_TMS_EXPENSE_DATA_ENTRY,
			ROLE_TRANSPORT_MANAGER,
			ROLE_TRANSPORT_ADMIN,
		):
			self.assertTrue(frappe.db.exists("Role", role), role)

		expected_profiles = {
			"TMS Trip Data Entry": {ROLE_TMS_TRIP_DATA_ENTRY},
			"TMS + Expense Data Entry": {ROLE_TMS_TRIP_DATA_ENTRY, ROLE_TMS_EXPENSE_DATA_ENTRY},
			"Transport Manager": {ROLE_TRANSPORT_MANAGER},
			"Transport Admin": {ROLE_TRANSPORT_ADMIN},
		}
		for profile, roles in expected_profiles.items():
			doc = frappe.get_doc("Role Profile", profile)
			self.assertEqual({row.role for row in doc.roles}, roles)

	def test_trip_data_entry_can_read_customer_but_cannot_create_or_write(self):
		self.assert_can(self.trip_user, "Customer", "read")
		self.assert_cannot(self.trip_user, "Customer", "create")
		self.assert_cannot(self.trip_user, "Customer", "write")
		self.assert_cannot(self.trip_user, "Customer", "delete")

	def test_trip_data_entry_can_read_supplier_but_cannot_create_or_write(self):
		self.assert_can(self.trip_user, "Supplier", "read")
		self.assert_cannot(self.trip_user, "Supplier", "create")
		self.assert_cannot(self.trip_user, "Supplier", "write")
		self.assert_cannot(self.trip_user, "Supplier", "delete")

	def test_trip_data_entry_can_create_and_edit_transport_trip(self):
		frappe.db.delete("Transport Trip", {"transport_job": self.demo["transport_job"]})
		material = "3/4 AGREEGAT(10MM-20MM)"
		frappe.db.set_value("Transport Job", self.demo["transport_job"], "material", material)
		frappe.db.set_value("Hired Vehicle", self.demo["hired_vehicle"], "vehicle_type", "TIPPER")

		frappe.set_user(self.trip_user)
		trip = frappe.new_doc("Transport Trip")
		trip.update({
			"transport_job": self.demo["transport_job"],
			"execution_source": "HIRED",
			"trip_date": "2026-09-09",
			"transporter": self.demo["transporter_supplier"],
			"hired_vehicle": self.demo["hired_vehicle"],
			"loading_site": self.demo["loading_site"],
			"unloading_site": self.demo["offloading_site"],
			"material": material,
			"planned_quantity": 1,
			"uom": self.demo["uom"],
		})
		trip.insert()
		trip.remarks = "RBAC edit allowed"
		trip.save()
		self.assertEqual(trip.owner, self.trip_user)

	def test_trip_data_entry_can_read_transport_job(self):
		frappe.set_user(self.trip_user)
		job = frappe.get_doc("Transport Job", self.demo["transport_job"])
		job.check_permission("read")
		self.assert_cannot(self.trip_user, "Transport Job", "write")

	def test_trip_data_entry_cannot_edit_protected_master_data(self):
		for doctype in ("Truck", "Truck Driver", "Hired Vehicle", "Transport Location", "Cargo Types", "Truck Type"):
			self.assert_can(self.trip_user, doctype, "read")
			self.assert_cannot(self.trip_user, doctype, "write")
			self.assert_cannot(self.trip_user, doctype, "delete")

	def test_trip_data_entry_cannot_access_data_import(self):
		frappe.set_user(self.trip_user)
		with self.assertRaises(frappe.PermissionError):
			base_importer.get_import_options()

	def test_expense_data_entry_retains_trip_access_and_can_create_purchase_invoice_draft(self):
		self.assert_can(self.expense_user, "Transport Trip", "create")
		self.assert_can(self.expense_user, "Transport Trip", "write")
		self.assert_can(self.expense_user, "Purchase Invoice", "create")
		self.assert_can(self.expense_user, "Purchase Invoice", "write")
		self.assert_cannot(self.expense_user, "Purchase Invoice", "submit")
		self.assert_cannot(self.expense_user, "Purchase Invoice", "cancel")
		self.assert_cannot(self.expense_user, "Purchase Invoice", "delete")

	def test_expense_data_entry_cannot_access_broad_accounting_configuration(self):
		self.assert_cannot(self.expense_user, "Account", "create")
		self.assert_cannot(self.expense_user, "Account", "write")
		self.assert_cannot(self.expense_user, "Company", "write")

	def test_transport_manager_can_manage_customer_supplier_and_tms_masters(self):
		for doctype in ("Customer", "Supplier"):
			self.assert_can(self.manager_user, doctype, "read")
			self.assert_can(self.manager_user, doctype, "create")
			self.assert_can(self.manager_user, doctype, "write")
			self.assert_cannot(self.manager_user, doctype, "delete")

		for doctype in (
			"Transport Location",
			"Cargo Types",
			"Truck Type",
			"Truck",
			"Truck Driver",
			"Hired Vehicle",
			"Transport Rate",
		):
			self.assert_can(self.manager_user, doctype, "create")
			self.assert_can(self.manager_user, doctype, "write")
			self.assert_cannot(self.manager_user, doctype, "delete")

		self.assert_can(self.manager_user, "Transport Sales Order", "create")
		self.assert_can(self.manager_user, "Transport Sales Order", "write")
		self.assert_can(self.manager_user, "Transport Sales Order", "submit")

	def test_transport_manager_has_current_sales_purchase_document_permissions(self):
		for doctype in ("Purchase Order", "Purchase Invoice", "Sales Invoice", "Sales Order"):
			if frappe.db.exists("DocType", doctype):
				self.assert_can(self.manager_user, doctype, "create")
				self.assert_can(self.manager_user, doctype, "write")
				self.assert_can(self.manager_user, doctype, "submit")

	def test_transport_admin_has_functional_tms_and_import_permissions(self):
		for doctype in (
			"Transport Job",
			"Transport Trip",
			"Truck",
			"Truck Driver",
			"Hired Vehicle",
			"Transport Location",
			"Cargo Types",
			"Truck Type",
			"Transport Rate",
			"Transport Sales Order",
			"TMS Import Log",
		):
			self.assert_can(self.admin_user, doctype, "create")
			self.assert_can(self.admin_user, doctype, "write")
			self.assert_can(self.admin_user, doctype, "delete")

		frappe.set_user(self.admin_user)
		self.assertIn("Transport Locations", [row["value"] for row in base_importer.get_import_options()["import_types"]])

	def test_administrator_remains_unrestricted(self):
		self.assert_can("Administrator", "User", "create")
		self.assert_can("Administrator", "Role", "write")

	def test_link_field_read_access_works_without_create_permission(self):
		frappe.set_user(self.trip_user)
		customer = frappe.get_doc("Customer", self.demo["customer"])
		supplier = frappe.get_doc("Supplier", self.demo["transporter_supplier"])
		customer.check_permission("read")
		supplier.check_permission("read")
		self.assert_cannot(self.trip_user, "Customer", "create")
		self.assert_cannot(self.trip_user, "Supplier", "create")

	def test_navigation_visibility_is_permission_backed_for_sensitive_tools(self):
		self.assert_cannot(self.trip_user, "TMS Import Log", "read")
		frappe.set_user(self.trip_user)
		with self.assertRaises(frappe.PermissionError):
			base_importer.get_import_options()
