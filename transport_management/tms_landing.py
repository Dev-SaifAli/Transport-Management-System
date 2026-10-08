"""Role-aware landing helpers for Transport Management."""

from __future__ import annotations

import frappe

AL_RANA_OPERATIONS_HOME = "desk/al-rana-operations"
AL_RANA_EXPENSES_HOME = "desk/al-rana-expenses"
AL_RANA_FINANCE_HOME = "desk/al-rana-finance"
AL_RANA_HR_HOME = "desk/al-rana-hr"
AL_RANA_ADMIN_HOME = "desk/al-rana-admin"
TRIP_OPERATIONS_HOME = "desk/tms-trip-operations"
ROLE_TMS_TRIP_DATA_ENTRY = "TMS Trip Data Entry"
AL_RANA_HOME_ROLES = {
	"TMS Trip Data Entry",
	"TMS + Expense Data Entry",
	"Transport Manager",
	"Transport Admin",
	"Accounts User",
	"Accounts Manager",
	"HR User",
	"HR Manager",
	"Expense Approver",
}
SENIOR_TMS_ROLES = {"Transport Manager", "Transport Admin", "System Manager"}
NON_BUSINESS_ROLES = {"All", "Guest", "Desk User"}


def get_tms_home_page(user=None):
	"""Return a role-aware AL RANA Desk landing route for office users."""
	user = user or frappe.session.user
	if is_al_rana_office_user(user):
		return get_al_rana_workspace_home(user)
	if is_pure_trip_data_entry_user(user):
		return TRIP_OPERATIONS_HOME
	return None


def get_al_rana_workspace_home(user):
	roles = set(frappe.get_roles(user))
	if roles.intersection({"System Manager", "Transport Admin"}):
		return AL_RANA_ADMIN_HOME
	if roles.intersection({"Accounts Manager", "Accounts User"}):
		return AL_RANA_FINANCE_HOME
	if roles.intersection({"HR Manager", "HR User"}):
		return AL_RANA_HR_HOME
	if "Expense Approver" in roles or "TMS + Expense Data Entry" in roles:
		return AL_RANA_EXPENSES_HOME
	return AL_RANA_OPERATIONS_HOME


def is_al_rana_office_user(user):
	if not user or user == "Administrator":
		return False
	roles = set(frappe.get_roles(user))
	return bool(roles.intersection(AL_RANA_HOME_ROLES))


def is_pure_trip_data_entry_user(user):
	if not user or user == "Administrator":
		return False

	roles = set(frappe.get_roles(user))
	if ROLE_TMS_TRIP_DATA_ENTRY not in roles:
		return False
	if roles.intersection(SENIOR_TMS_ROLES):
		return False

	business_roles = roles - NON_BUSINESS_ROLES
	return business_roles == {ROLE_TMS_TRIP_DATA_ENTRY}
