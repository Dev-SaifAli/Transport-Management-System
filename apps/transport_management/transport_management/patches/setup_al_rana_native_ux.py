"""Configure native AL RANA Desk UX visibility controls."""

from __future__ import annotations

import frappe


TRANSPORT_MANAGEMENT_WORKSPACE_ROLES = {
	"Transport Manager",
	"Transport Admin",
	"System Manager",
	"TMS Trip Data Entry",
	"TMS + Expense Data Entry",
	"Expense Approver",
	"Accounts User",
	"Accounts Manager",
	"HR User",
	"HR Manager",
}

PROFILE_MODULE_BLOCKS = {
	"AL RANA Dispatcher Profile": {
		"Accounts",
		"Assets",
		"Automation",
		"Buying",
		"CRM",
		"Communication",
		"EDI",
		"ERPNext Integrations",
		"Email",
		"Fleet Managment",
		"Geo",
		"HR",
		"Integrations",
		"Maintenance",
		"Manufacturing",
		"Payroll",
		"Portal",
		"Printing",
		"Projects",
		"Quality Management",
		"Regional",
		"Selling",
		"Stock",
		"Subcontracting",
		"Support",
		"Telephony",
		"Utilities",
		"VSD Fleet MS",
		"Website",
		"Workflow",
	},
	"AL RANA Expense Profile": {
		"Assets",
		"Automation",
		"Buying",
		"CRM",
		"Communication",
		"EDI",
		"ERPNext Integrations",
		"Email",
		"Fleet Managment",
		"Geo",
		"Maintenance",
		"Manufacturing",
		"Payroll",
		"Portal",
		"Printing",
		"Projects",
		"Quality Management",
		"Regional",
		"Selling",
		"Stock",
		"Subcontracting",
		"Support",
		"Telephony",
		"Utilities",
		"VSD Fleet MS",
		"Website",
		"Workflow",
	},
	"AL RANA Accounts Profile": {
		"Automation",
		"CRM",
		"Communication",
		"EDI",
		"ERPNext Integrations",
		"Email",
		"Fleet Managment",
		"Geo",
		"HR",
		"Integrations",
		"Maintenance",
		"Manufacturing",
		"Payroll",
		"Portal",
		"Projects",
		"Quality Management",
		"Stock",
		"Subcontracting",
		"Support",
		"Telephony",
		"VSD Fleet MS",
		"Website",
	},
	"AL RANA HR Profile": {
		"Accounts",
		"Assets",
		"Automation",
		"Buying",
		"CRM",
		"Communication",
		"EDI",
		"ERPNext Integrations",
		"Email",
		"Fleet Managment",
		"Geo",
		"Maintenance",
		"Manufacturing",
		"Portal",
		"Projects",
		"Quality Management",
		"Regional",
		"Selling",
		"Stock",
		"Subcontracting",
		"Support",
		"Telephony",
		"Utilities",
		"VSD Fleet MS",
		"Website",
	},
}

PROFILE_ASSIGNMENTS = [
	({"TMS Trip Data Entry"}, "AL RANA Dispatcher Profile", "Transport Management"),
	({"TMS + Expense Data Entry", "Expense Approver"}, "AL RANA Expense Profile", "Transport Management"),
	({"Accounts Manager", "Accounts User"}, "AL RANA Accounts Profile", "Transport Management"),
	({"HR Manager", "HR User"}, "AL RANA HR Profile", "Transport Management"),
]

ADMIN_ROLES = {"System Manager", "Transport Admin"}


def execute():
	ensure_transport_management_workspace_roles()
	ensure_module_profiles()
	assign_profiles_to_existing_users()
	frappe.clear_cache()


def ensure_transport_management_workspace_roles():
	if not frappe.db.exists("Workspace", "Transport Management"):
		return

	doc = frappe.get_doc("Workspace", "Transport Management")
	existing = {row.role for row in doc.roles}
	for role in sorted(TRANSPORT_MANAGEMENT_WORKSPACE_ROLES - existing):
		doc.append("roles", {"role": role})
	for row in list(doc.roles):
		if row.role not in TRANSPORT_MANAGEMENT_WORKSPACE_ROLES:
			doc.remove(row)
	doc.flags.ignore_permissions = True
	doc.save()


def ensure_module_profiles():
	available_modules = set(frappe.get_all("Module Def", pluck="name"))
	for profile_name, blocked_modules in PROFILE_MODULE_BLOCKS.items():
		modules = sorted(blocked_modules & available_modules)
		doc = get_or_create_module_profile(profile_name)
		if not doc.is_new():
			existing_modules = [row.module for row in doc.block_modules]
			if set(existing_modules) == set(modules) and len(existing_modules) == len(modules):
				continue
		doc.set("block_modules", [])
		for module in modules:
			doc.append("block_modules", {"module": module})
		doc.flags.ignore_permissions = True
		doc.save()


def get_or_create_module_profile(profile_name: str):
	if frappe.db.exists("Module Profile", profile_name):
		return frappe.get_doc("Module Profile", profile_name)
	return frappe.get_doc(
		{
			"doctype": "Module Profile",
			"module_profile_name": profile_name,
		}
	)


def assign_profiles_to_existing_users():
	for user_name in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
		if user_name in {"Administrator", "Guest"}:
			continue

		roles = set(frappe.get_roles(user_name))
		if roles & ADMIN_ROLES:
			continue

		for matching_roles, profile_name, default_workspace in PROFILE_ASSIGNMENTS:
			if roles & matching_roles:
				apply_user_native_ux(user_name, profile_name, default_workspace)
				break


def apply_user_native_ux(user_name: str, profile_name: str, default_workspace: str):
	user = frappe.get_doc("User", user_name)
	changed = False

	profile = frappe.get_doc("Module Profile", profile_name)
	profile_modules = {row.module for row in profile.block_modules}
	user_modules = {row.module for row in user.block_modules}
	if user.module_profile != profile_name or user_modules != profile_modules:
		user.module_profile = profile_name
		user.set("block_modules", [])
		for row in profile.block_modules:
			user.append("block_modules", {"module": row.module})
		changed = True

	if frappe.db.exists("Workspace", default_workspace) and user.default_workspace != default_workspace:
		user.default_workspace = default_workspace
		changed = True

	if changed:
		user.flags.ignore_permissions = True
		user.save()
