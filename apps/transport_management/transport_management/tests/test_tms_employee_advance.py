"""Tests for AL RANA Employee Advance defaults and guardrails."""

import unittest

import frappe

from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

from transport_management.tms_employee_advance import (
	AL_RANA_COMPANY,
	get_al_rana_employee_advance_defaults,
	get_employee_advance_defaults,
)


class TestTMSEmployeeAdvance(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("tms_employee_advance")
		self.ensure_gender("Male")

	def tearDown(self):
		frappe.db.rollback(save_point="tms_employee_advance")

	def ensure_gender(self, gender):
		if not frappe.db.exists("Gender", gender):
			frappe.get_doc({"doctype": "Gender", "gender": gender}).insert(ignore_permissions=True)

	def make_employee(self, company=AL_RANA_COMPANY):
		return frappe.get_doc({
			"doctype": "Employee",
			"first_name": f"TMS Advance {frappe.generate_hash(length=8)}",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2026-01-01",
			"company": company,
			"status": "Active",
		}).insert(ignore_permissions=True)

	def make_advance(self, employee, **values):
		doc = frappe.get_doc({
			"doctype": "Employee Advance",
			"employee": employee.name,
			"posting_date": "2026-10-05",
			"purpose": "Driver Standing Float",
			"advance_amount": 500,
			"company": employee.company,
		})
		doc.update(values)
		return doc

	def test_al_rana_defaults_are_configured(self):
		defaults = get_al_rana_employee_advance_defaults()
		account = frappe.db.get_value(
			"Account",
			defaults["advance_account"],
			["company", "root_type", "account_type", "account_currency", "is_group", "disabled"],
			as_dict=True,
		)

		self.assertEqual(defaults["currency"], "AED")
		self.assertEqual(defaults["advance_account"], "Employee Advances - ARL")
		self.assertEqual(account.company, AL_RANA_COMPANY)
		self.assertEqual(account.root_type, "Asset")
		self.assertEqual(account.account_type, "Receivable")
		self.assertEqual(account.account_currency, "AED")
		self.assertFalse(account.is_group)
		self.assertFalse(account.disabled)

	def test_new_al_rana_advance_gets_currency_and_account(self):
		employee = self.make_employee()
		doc = self.make_advance(employee)
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.currency, "AED")
		self.assertEqual(doc.advance_account, "Employee Advances - ARL")

	def test_al_rana_defaults_api_returns_approved_account_only(self):
		employee = self.make_employee()

		defaults = get_employee_advance_defaults(employee=employee.name)

		self.assertEqual(defaults["company"], AL_RANA_COMPANY)
		self.assertEqual(defaults["currency"], "AED")
		self.assertEqual(defaults["advance_account"], "Employee Advances - ARL")
		self.assertNotEqual(defaults["advance_account"], "Debtors - ARL")

	def test_wrong_al_rana_receivable_account_is_rejected(self):
		employee = self.make_employee()
		doc = self.make_advance(employee, currency="AED", advance_account="Debtors - ARL")

		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_existing_valid_account_remains_unchanged(self):
		employee = self.make_employee()
		doc = self.make_advance(employee, currency="AED", advance_account="Employee Advances - ARL")
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.advance_account, "Employee Advances - ARL")
		self.assertEqual(doc.currency, "AED")

	def test_other_company_keeps_standard_behavior(self):
		other_company = frappe.db.get_value("Company", {"name": ("!=", AL_RANA_COMPANY)}, "name")
		if not other_company:
			self.skipTest("No non-AL RANA company available")

		defaults = get_employee_advance_defaults(company=other_company)

		self.assertEqual(defaults, {})

	def test_create_payment_uses_employee_advance_account(self):
		employee = self.make_employee()
		doc = self.make_advance(employee, mode_of_payment="Cash")
		doc.insert(ignore_permissions=True)
		doc.submit()

		payment = get_payment_entry_for_employee("Employee Advance", doc.name)

		self.assertEqual(payment.payment_type, "Pay")
		self.assertEqual(payment.party_type, "Employee")
		self.assertEqual(payment.party, employee.name)
		self.assertEqual(payment.paid_from, "Cash - ARL")
		self.assertEqual(payment.paid_to, "Employee Advances - ARL")
		self.assertEqual(payment.references[0].reference_doctype, "Employee Advance")
		self.assertEqual(payment.references[0].reference_name, doc.name)
		self.assertEqual(payment.references[0].allocated_amount, 500)

	def test_expense_claim_company_payable_account_is_unchanged(self):
		payable_account = frappe.db.get_value(
			"Company",
			AL_RANA_COMPANY,
			"default_expense_claim_payable_account",
		)

		self.assertEqual(payable_account, "Creditors - ARL")
