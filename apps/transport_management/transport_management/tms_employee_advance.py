"""AL RANA Employee Advance defaults and guardrails."""

import frappe
from frappe import _

AL_RANA_COMPANY = "AL RANA TRANSPORT LLC"


@frappe.whitelist()
def get_employee_advance_defaults(employee=None, company=None):
	company = get_employee_advance_company(employee=employee, company=company)
	if company != AL_RANA_COMPANY:
		return {}

	defaults = get_al_rana_employee_advance_defaults()
	return {
		"company": company,
		"currency": defaults["currency"],
		"advance_account": defaults["advance_account"],
	}


def normalize_employee_advance_defaults(doc, method=None):
	company = get_employee_advance_company(employee=doc.employee, company=doc.company)
	if company != AL_RANA_COMPANY:
		return

	defaults = get_al_rana_employee_advance_defaults()
	if not doc.company:
		doc.company = company
	if not doc.currency:
		doc.currency = defaults["currency"]
	if not doc.advance_account:
		doc.advance_account = defaults["advance_account"]

	if doc.currency != defaults["currency"]:
		frappe.throw(
			_("For {0}, Employee Advance currency must be {1}.").format(
				AL_RANA_COMPANY,
				frappe.bold(defaults["currency"]),
			)
		)

	if doc.advance_account != defaults["advance_account"]:
		frappe.throw(
			_("For {0}, Employee Advance must use {1}.").format(
				AL_RANA_COMPANY,
				frappe.bold(defaults["advance_account"]),
			)
		)


def get_employee_advance_company(employee=None, company=None):
	if company:
		return company
	if employee:
		return frappe.db.get_value("Employee", employee, "company")
	return None


def get_al_rana_employee_advance_defaults():
	company = frappe.db.get_value(
		"Company",
		AL_RANA_COMPANY,
		["default_currency", "default_employee_advance_account"],
		as_dict=True,
	)
	if not company:
		frappe.throw(_("Company {0} does not exist.").format(AL_RANA_COMPANY))

	if not company.default_currency:
		frappe.throw(_("Please set Default Currency for Company {0}.").format(AL_RANA_COMPANY))

	if not company.default_employee_advance_account:
		frappe.throw(
			_("Please set Default Employee Advance Account for Company {0}.").format(AL_RANA_COMPANY)
		)

	validate_employee_advance_account(company.default_employee_advance_account, company.default_currency)
	return {
		"currency": company.default_currency,
		"advance_account": company.default_employee_advance_account,
	}


def validate_employee_advance_account(account, currency):
	account_details = frappe.db.get_value(
		"Account",
		account,
		["company", "root_type", "account_type", "account_currency", "is_group", "disabled"],
		as_dict=True,
	)
	if not account_details:
		frappe.throw(_("Employee Advance Account {0} does not exist.").format(account))

	if account_details.company != AL_RANA_COMPANY:
		frappe.throw(_("Employee Advance Account {0} does not belong to {1}.").format(account, AL_RANA_COMPANY))

	if account_details.is_group:
		frappe.throw(_("Employee Advance Account {0} must not be a group account.").format(account))

	if account_details.disabled:
		frappe.throw(_("Employee Advance Account {0} is disabled.").format(account))

	if account_details.root_type != "Asset" or account_details.account_type != "Receivable":
		frappe.throw(
			_("Employee Advance Account {0} must be an Asset account of type Receivable.").format(account)
		)

	if account_details.account_currency != currency:
		frappe.throw(
			_("Employee Advance Account {0} currency must be {1}.").format(
				account,
				frappe.bold(currency),
			)
		)
