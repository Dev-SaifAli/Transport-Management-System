"""Role-aware landing helpers for Transport Management."""

from __future__ import annotations

import frappe

TRIP_OPERATIONS_HOME = "desk/tms-trip-operations"
ROLE_TMS_TRIP_DATA_ENTRY = "TMS Trip Data Entry"
SENIOR_TMS_ROLES = {"Transport Manager", "Transport Admin", "System Manager"}
NON_BUSINESS_ROLES = {"All", "Guest", "Desk User"}


def get_tms_home_page(user=None):
	"""Return a TMS Desk landing route for pure operational Trip users."""
	user = user or frappe.session.user
	if is_pure_trip_data_entry_user(user):
		return TRIP_OPERATIONS_HOME
	return None


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
