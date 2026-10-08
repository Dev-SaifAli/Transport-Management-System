"""Tests for TMS context on standard HRMS Expense Claims."""

import unittest

import frappe
from frappe.modules import reload_doc

from transport_management.tms_driver_expense import (
	EXPENSE_CLAIM_TYPES,
	ensure_driver_expense_foundation,
	get_expense_claim_detail_tms_defaults,
	get_expense_claim_header_defaults,
	get_driver_employee_mapping_summary,
	normalize_expense_claim_tms_references,
	resolve_expense_claim_header_defaults,
)


class TestDriverExpenseFoundation(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_job", force=True)
		reload_doc("transport_management", "doctype", "transport_trip", force=True)

	def setUp(self):
		frappe.db.savepoint("driver_expense_foundation")
		ensure_driver_expense_foundation()
		self.fixture = self.make_fixture()

	def tearDown(self):
		frappe.db.rollback(save_point="driver_expense_foundation")

	def make_fixture(self):
		suffix = frappe.generate_hash(length=8)
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_value("Company", {})
		country = frappe.db.get_value("Country", "United Arab Emirates") or frappe.db.get_value("Country", {})
		self.ensure_uom("TON")
		self.ensure_truck_type("TIPPER")
		self.ensure_gender("Male")

		employee = frappe.get_doc({
			"doctype": "Employee",
			"first_name": "TMS Driver Expense",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2026-01-01",
			"company": company,
			"status": "Active",
		}).insert(ignore_permissions=True)
		driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"TMS Expense Driver {suffix}",
			"status": "Active",
			"cell_number": f"EXP-{suffix}",
			"employee": employee.name,
		}).insert(ignore_permissions=True)
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": f"TMS Expense Customer {suffix}",
			"customer_type": "Company",
		}).insert(ignore_permissions=True)
		supplier = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": f"TMS Expense Transporter {suffix}",
			"supplier_type": "Company",
			"is_transporter": 1,
			"transporter_status": "Active",
		}).insert(ignore_permissions=True)
		material = frappe.get_doc({
			"doctype": "Cargo Types",
			"cargo_name": f"TMS Expense Material {suffix}",
			"active": 1,
			"allowed_truck_types": [{"truck_type": "TIPPER"}],
		}).insert(ignore_permissions=True)
		loading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"TMS Expense Loading {suffix}",
			"country": country,
			"location_usage": "Loading",
			"location_type": "Plant",
			"active": 1,
		}).insert(ignore_permissions=True)
		unloading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"TMS Expense Unloading {suffix}",
			"country": country,
			"location_usage": "Unloading",
			"location_type": "Customer Site",
			"customer": customer.name,
			"active": 1,
		}).insert(ignore_permissions=True)
		truck = frappe.get_doc({
			"doctype": "Truck",
			"truck_number": f"TMS-EXP-{suffix}",
			"license_plate": f"TMS-EXP-{suffix}",
			"vehicle_type": "TIPPER",
			"ownership_type": "OWN",
			"status": "Idle",
			"disabled": 0,
		}).insert(ignore_permissions=True)
		hired_vehicle = frappe.get_doc({
			"doctype": "Hired Vehicle",
			"transporter": supplier.name,
			"plate_number": f"HV-EXP-{suffix}",
			"vehicle_type": "TIPPER",
			"active": 1,
		}).insert(ignore_permissions=True)
		return {
			"company": company,
			"employee": employee.name,
			"driver": driver.name,
			"customer": customer.name,
			"transporter": supplier.name,
			"material": material.name,
			"loading_site": loading_site.name,
			"unloading_site": unloading_site.name,
			"truck": truck.name,
			"hired_vehicle": hired_vehicle.name,
		}

	def ensure_uom(self, uom):
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom, "enabled": 1}).insert(ignore_permissions=True)

	def ensure_truck_type(self, truck_type):
		if not frappe.db.exists("Truck Type", truck_type):
			frappe.get_doc({"doctype": "Truck Type", "truck_type": truck_type}).insert(ignore_permissions=True)

	def ensure_gender(self, gender):
		if not frappe.db.exists("Gender", gender):
			frappe.get_doc({"doctype": "Gender", "gender": gender}).insert(ignore_permissions=True)

	def make_department(self, department_name=None):
		department_name = department_name or f"TMS Expense Department {frappe.generate_hash(length=8)}"
		return frappe.get_doc({
			"doctype": "Department",
			"department_name": department_name,
			"company": self.fixture["company"],
		}).insert(ignore_permissions=True)

	def make_user(self, email=None):
		email = email or f"tms-expense-{frappe.generate_hash(length=8)}@example.com"
		if frappe.db.exists("User", email):
			return frappe.get_doc("User", email)

		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": "TMS",
			"last_name": "Expense Approver",
			"enabled": 1,
			"user_type": "System User",
			"send_welcome_email": 0,
		}).insert(ignore_permissions=True)
		user.add_roles("Expense Approver")
		return user

	def make_employee(self, **values):
		doc = frappe.get_doc({
			"doctype": "Employee",
			"first_name": values.pop("first_name", "TMS Expense Employee"),
			"gender": values.pop("gender", "Male"),
			"date_of_birth": values.pop("date_of_birth", "1990-01-01"),
			"date_of_joining": values.pop("date_of_joining", "2026-01-01"),
			"company": values.pop("company", self.fixture["company"]),
			"status": values.pop("status", "Active"),
		})
		doc.update(values)
		return doc.insert(ignore_permissions=True)

	def make_job(self, **values):
		doc = frappe.new_doc("Transport Job")
		doc.update({
			"customer": self.fixture["customer"],
			"requested_date": "2026-10-03",
			"loading_site": self.fixture["loading_site"],
			"unloading_site": self.fixture["unloading_site"],
			"material": self.fixture["material"],
			"requested_quantity": 20,
			"uom": "TON",
		})
		doc.update(values)
		doc.insert(ignore_permissions=True)
		return doc

	def make_trip(self, job, **values):
		doc = frappe.new_doc("Transport Trip")
		doc.update({
			"transport_job": job.name,
			"execution_source": "OWN",
			"trip_date": job.requested_date,
			"vehicle": self.fixture["truck"],
			"driver": self.fixture["driver"],
			"loading_site": job.loading_site,
			"unloading_site": job.unloading_site,
			"material": job.material,
			"planned_quantity": 10,
			"uom": "TON",
		})
		doc.update(values)
		doc.insert(ignore_permissions=True)
		return doc

	def make_expense_claim(self, rows):
		return frappe.get_doc({
			"doctype": "Expense Claim",
			"employee": self.fixture["employee"],
			"company": self.fixture["company"],
			"posting_date": "2026-10-03",
			"approval_status": "Draft",
			"expenses": rows,
		})

	def test_expense_claim_detail_custom_fields_are_installed(self):
		meta = frappe.get_meta("Expense Claim Detail", cached=False)
		expected = {
			"transport_trip": ("Link", "Transport Trip"),
			"transport_job": ("Link", "Transport Job"),
			"truck": ("Link", "Truck"),
			"hired_vehicle": ("Link", "Hired Vehicle"),
		}
		for fieldname, (fieldtype, options) in expected.items():
			field = meta.get_field(fieldname)
			self.assertIsNotNone(field)
			self.assertEqual(field.fieldtype, fieldtype)
			self.assertEqual(field.options, options)
			self.assertFalse(field.reqd)

	def test_expense_claim_detail_can_exist_without_tms_refs(self):
		doc = self.make_expense_claim([{"expense_type": "Toll", "amount": 200, "sanctioned_amount": 200}])
		normalize_expense_claim_tms_references(doc)
		row = doc.expenses[0]
		self.assertFalse(row.get("transport_trip"))
		self.assertFalse(row.get("transport_job"))
		self.assertFalse(row.get("truck"))
		self.assertFalse(row.get("hired_vehicle"))

	def test_employee_department_populates_expense_claim_header(self):
		department = self.make_department()
		employee = self.make_employee(department=department.name)
		doc = self.make_expense_claim([{"expense_type": "Toll", "amount": 200}])
		doc.employee = employee.name
		doc.department = None

		normalize_expense_claim_tms_references(doc)

		self.assertEqual(doc.department, department.name)

	def test_employee_direct_expense_approver_populates_header(self):
		approver = self.make_user()
		employee = self.make_employee(expense_approver=approver.name)
		doc = self.make_expense_claim([{"expense_type": "Toll", "amount": 200}])
		doc.employee = employee.name

		normalize_expense_claim_tms_references(doc)

		self.assertEqual(doc.expense_approver, approver.name)

	def test_department_expense_approver_populates_header(self):
		department = self.make_department()
		approver = self.make_user()
		department.append("expense_approvers", {"approver": approver.name})
		department.save(ignore_permissions=True)
		employee = self.make_employee(department=department.name)
		doc = self.make_expense_claim([{"expense_type": "Toll", "amount": 200}])
		doc.employee = employee.name

		normalize_expense_claim_tms_references(doc)

		self.assertEqual(doc.department, department.name)
		self.assertEqual(doc.expense_approver, approver.name)

	def test_direct_expense_approver_takes_priority_over_department(self):
		department = self.make_department()
		department_approver = self.make_user()
		direct_approver = self.make_user()
		department.append("expense_approvers", {"approver": department_approver.name})
		department.save(ignore_permissions=True)
		employee = self.make_employee(
			department=department.name,
			expense_approver=direct_approver.name,
		)

		defaults = resolve_expense_claim_header_defaults(employee.name)

		self.assertEqual(defaults["department"], department.name)
		self.assertEqual(defaults["expense_approver"], direct_approver.name)

	def test_different_departments_resolve_different_approvers(self):
		first_department = self.make_department()
		second_department = self.make_department()
		first_approver = self.make_user()
		second_approver = self.make_user()
		first_department.append("expense_approvers", {"approver": first_approver.name})
		second_department.append("expense_approvers", {"approver": second_approver.name})
		first_department.save(ignore_permissions=True)
		second_department.save(ignore_permissions=True)
		first_employee = self.make_employee(department=first_department.name)
		second_employee = self.make_employee(department=second_department.name)

		first_defaults = resolve_expense_claim_header_defaults(first_employee.name)
		second_defaults = resolve_expense_claim_header_defaults(second_employee.name)

		self.assertEqual(first_defaults["expense_approver"], first_approver.name)
		self.assertEqual(second_defaults["expense_approver"], second_approver.name)

	def test_employee_without_department_or_approver_is_safe(self):
		employee = self.make_employee()

		defaults = resolve_expense_claim_header_defaults(employee.name)

		self.assertFalse(defaults["department"])
		self.assertFalse(defaults["expense_approver"])

	def test_manual_expense_approver_is_not_overwritten(self):
		configured_approver = self.make_user()
		manual_approver = self.make_user()
		employee = self.make_employee(expense_approver=configured_approver.name)
		doc = self.make_expense_claim([{"expense_type": "Toll", "amount": 200}])
		doc.employee = employee.name
		doc.expense_approver = manual_approver.name

		normalize_expense_claim_tms_references(doc)

		self.assertEqual(doc.expense_approver, manual_approver.name)

	def test_client_defaults_api_returns_header_values(self):
		department = self.make_department()
		approver = self.make_user()
		employee = self.make_employee(department=department.name, expense_approver=approver.name)

		defaults = get_expense_claim_header_defaults(employee.name)

		self.assertEqual(defaults["department"], department.name)
		self.assertEqual(defaults["expense_approver"], approver.name)

	def test_trip_selection_derives_job(self):
		job = self.make_job()
		trip = self.make_trip(job)
		doc = self.make_expense_claim([{"expense_type": "Toll", "amount": 200, "transport_trip": trip.name}])
		normalize_expense_claim_tms_references(doc)
		self.assertEqual(doc.expenses[0].transport_job, job.name)

	def test_own_trip_derives_truck_and_clears_hired_vehicle(self):
		job = self.make_job()
		trip = self.make_trip(job)
		doc = self.make_expense_claim([{
			"expense_type": "Fuel",
			"amount": 100,
			"transport_trip": trip.name,
			"hired_vehicle": self.fixture["hired_vehicle"],
		}])
		normalize_expense_claim_tms_references(doc)
		row = doc.expenses[0]
		self.assertEqual(row.truck, self.fixture["truck"])
		self.assertFalse(row.hired_vehicle)

	def test_hired_trip_derives_hired_vehicle_and_clears_truck(self):
		job = self.make_job()
		trip = self.make_trip(
			job,
			execution_source="HIRED",
			vehicle=None,
			driver=None,
			transporter=self.fixture["transporter"],
			hired_vehicle=self.fixture["hired_vehicle"],
		)
		doc = self.make_expense_claim([{
			"expense_type": "Parking",
			"amount": 75,
			"transport_trip": trip.name,
			"truck": self.fixture["truck"],
		}])
		normalize_expense_claim_tms_references(doc)
		row = doc.expenses[0]
		self.assertFalse(row.truck)
		self.assertEqual(row.hired_vehicle, self.fixture["hired_vehicle"])

	def test_conflicting_trip_job_is_normalized_to_trip_job(self):
		correct_job = self.make_job()
		wrong_job = self.make_job()
		trip = self.make_trip(correct_job)
		doc = self.make_expense_claim([{
			"expense_type": "Toll",
			"amount": 50,
			"transport_trip": trip.name,
			"transport_job": wrong_job.name,
		}])
		normalize_expense_claim_tms_references(doc)
		self.assertEqual(doc.expenses[0].transport_job, correct_job.name)

	def test_conflicting_vehicle_refs_without_trip_are_rejected(self):
		job = self.make_job()
		doc = self.make_expense_claim([{
			"expense_type": "Other",
			"amount": 30,
			"transport_job": job.name,
			"truck": self.fixture["truck"],
			"hired_vehicle": self.fixture["hired_vehicle"],
		}])
		with self.assertRaises(frappe.ValidationError):
			normalize_expense_claim_tms_references(doc)

	def test_job_only_row_remains_valid(self):
		job = self.make_job()
		doc = self.make_expense_claim([{"expense_type": "Other", "amount": 25, "transport_job": job.name}])
		normalize_expense_claim_tms_references(doc)
		self.assertEqual(doc.expenses[0].transport_job, job.name)
		self.assertFalse(doc.expenses[0].transport_trip)

	def test_multiple_rows_can_reference_different_trips(self):
		first_job = self.make_job()
		second_job = self.make_job()
		first_trip = self.make_trip(first_job)
		second_trip = self.make_trip(
			second_job,
			execution_source="HIRED",
			vehicle=None,
			driver=None,
			transporter=self.fixture["transporter"],
			hired_vehicle=self.fixture["hired_vehicle"],
		)
		doc = self.make_expense_claim([
			{"expense_type": "Toll", "amount": 50, "transport_trip": first_trip.name},
			{"expense_type": "Parking", "amount": 40, "transport_trip": second_trip.name},
		])
		normalize_expense_claim_tms_references(doc)
		self.assertEqual(doc.expenses[0].transport_job, first_job.name)
		self.assertEqual(doc.expenses[0].truck, self.fixture["truck"])
		self.assertEqual(doc.expenses[1].transport_job, second_job.name)
		self.assertEqual(doc.expenses[1].hired_vehicle, self.fixture["hired_vehicle"])

	def test_expense_claim_types_are_not_duplicated(self):
		before = {name: frappe.db.count("Expense Claim Type", {"name": name}) for name in EXPENSE_CLAIM_TYPES}
		ensure_driver_expense_foundation()
		ensure_driver_expense_foundation()
		after = {name: frappe.db.count("Expense Claim Type", {"name": name}) for name in EXPENSE_CLAIM_TYPES}
		self.assertEqual(before, after)
		self.assertTrue(all(count == 1 for count in after.values()))

	def test_standing_employee_advance_is_not_auto_allocated(self):
		advance = frappe.get_doc({
			"doctype": "Employee Advance",
			"employee": self.fixture["employee"],
			"posting_date": "2026-10-03",
			"purpose": "Standing driver float",
			"advance_amount": 500,
			"company": self.fixture["company"],
		})
		advance.insert(ignore_permissions=True)
		job = self.make_job()
		trip = self.make_trip(job)
		doc = self.make_expense_claim([{"expense_type": "Toll", "amount": 200, "transport_trip": trip.name}])
		normalize_expense_claim_tms_references(doc)
		self.assertFalse(doc.get("advances"))
		self.assertEqual(advance.claimed_amount or 0, 0)

	def test_truck_driver_employee_mapping_summary_reports_unmapped(self):
		summary = get_driver_employee_mapping_summary()
		self.assertGreaterEqual(summary["total_drivers"], 1)
		self.assertTrue(any(driver.employee == self.fixture["employee"] for driver in frappe.get_all("Truck Driver", fields=["employee"])))

	def test_client_defaults_api_matches_trip(self):
		job = self.make_job()
		trip = self.make_trip(job)
		defaults = get_expense_claim_detail_tms_defaults(transport_trip=trip.name)
		self.assertEqual(defaults["transport_trip"], trip.name)
		self.assertEqual(defaults["transport_job"], job.name)
		self.assertEqual(defaults["truck"], self.fixture["truck"])
		self.assertFalse(defaults["hired_vehicle"])
