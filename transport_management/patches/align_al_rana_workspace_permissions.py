"""Align standard DocType permissions with AL RANA native workspaces."""

from __future__ import annotations

import frappe


PERMISSIONS = [
	# Expense operations: draft entry only, approval stays with HRMS approver roles.
	{
		"parent": "Expense Claim",
		"role": "TMS + Expense Data Entry",
		"if_owner": 1,
		"read": 1,
		"write": 1,
		"create": 1,
		"report": 1,
		"export": 1,
	},
	{
		"parent": "Employee Advance",
		"role": "TMS + Expense Data Entry",
		"if_owner": 1,
		"read": 1,
		"write": 1,
		"create": 1,
		"report": 1,
		"export": 1,
	},
	# HR workspace links.
	{
		"parent": "Employee",
		"role": "HR User",
		"read": 1,
		"write": 1,
		"create": 1,
		"report": 1,
		"export": 1,
		"import": 1,
	},
	{
		"parent": "Employee",
		"role": "HR Manager",
		"read": 1,
		"write": 1,
		"create": 1,
		"report": 1,
		"export": 1,
		"import": 1,
	},
	{
		"parent": "Employee Advance",
		"role": "HR User",
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"report": 1,
		"export": 1,
	},
	{
		"parent": "Employee Advance",
		"role": "HR Manager",
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"cancel": 1,
		"amend": 1,
		"report": 1,
		"export": 1,
	},
	# Finance workspace links for accounting roles.
	{
		"parent": "Sales Invoice",
		"role": "Accounts User",
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"cancel": 1,
		"amend": 1,
		"report": 1,
		"export": 1,
		"import": 1,
	},
	{
		"parent": "Sales Invoice",
		"role": "Accounts Manager",
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"cancel": 1,
		"amend": 1,
		"report": 1,
		"export": 1,
		"import": 1,
	},
	{
		"parent": "Purchase Invoice",
		"role": "Accounts User",
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"cancel": 1,
		"amend": 1,
		"report": 1,
		"export": 1,
		"import": 1,
	},
	{
		"parent": "Purchase Invoice",
		"role": "Accounts Manager",
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"cancel": 1,
		"amend": 1,
		"report": 1,
		"export": 1,
		"import": 1,
	},
	# Operations oversight of driver expenses (AL RANA Expenses workspace links).
	# Read-only: approval separation stays with HRMS approver roles.
	{
		"parent": "Expense Claim",
		"role": "Transport Manager",
		"read": 1,
		"report": 1,
		"export": 1,
	},
	{
		"parent": "Expense Claim",
		"role": "Transport Admin",
		"read": 1,
		"report": 1,
		"export": 1,
	},
	{
		"parent": "Employee Advance",
		"role": "Transport Manager",
		"read": 1,
		"report": 1,
		"export": 1,
	},
	{
		"parent": "Employee Advance",
		"role": "Transport Admin",
		"read": 1,
		"report": 1,
		"export": 1,
	},
	# Link/master visibility required by the above standard workflows.
	{"parent": "Customer", "role": "Accounts User", "read": 1, "report": 1, "export": 1},
	{"parent": "Customer", "role": "Accounts Manager", "read": 1, "report": 1, "export": 1},
	{"parent": "Supplier", "role": "Accounts User", "read": 1, "report": 1, "export": 1},
	{"parent": "Supplier", "role": "Accounts Manager", "read": 1, "report": 1, "export": 1},
	{"parent": "Customer", "role": "TMS + Expense Data Entry", "read": 1, "report": 1, "export": 1},
	{"parent": "Supplier", "role": "TMS + Expense Data Entry", "read": 1, "report": 1, "export": 1},
]

PAGE_ROLES = {
	"tms-data-import": {"System Manager", "Transport Admin"},
	"tms-trip-operations": {
		"System Manager",
		"TMS Trip Data Entry",
		"TMS + Expense Data Entry",
		"Transport Manager",
		"Transport Admin",
	},
}


def execute():
	for permission in PERMISSIONS:
		upsert_custom_docperm(permission)
	for page, roles in PAGE_ROLES.items():
		ensure_page_roles(page, roles)
	frappe.clear_cache()


def upsert_custom_docperm(permission: dict):
	defaults = {
		"permlevel": 0,
		"if_owner": 0,
		"read": 0,
		"write": 0,
		"create": 0,
		"delete": 0,
		"submit": 0,
		"cancel": 0,
		"amend": 0,
		"report": 0,
		"export": 0,
		"import": 0,
		"select": 0,
		"share": 0,
		"print": 1,
		"email": 1,
	}
	values = {**defaults, **permission}
	name = frappe.db.exists(
		"Custom DocPerm",
		{
			"parent": values["parent"],
			"role": values["role"],
			"permlevel": values["permlevel"],
		},
	)
	if name:
		doc = frappe.get_doc("Custom DocPerm", name)
		for field, value in values.items():
			doc.set(field, value)
	else:
		doc = frappe.get_doc({"doctype": "Custom DocPerm", **values})
	doc.flags.ignore_permissions = True
	doc.save()


def ensure_page_roles(page: str, roles: set[str]):
	if not frappe.db.exists("Page", page):
		return
	doc = frappe.get_doc("Page", page)
	existing = {row.role for row in doc.roles}
	for role in sorted(roles - existing):
		doc.append("roles", {"role": role})
	doc.flags.ignore_permissions = True
	doc.save()
