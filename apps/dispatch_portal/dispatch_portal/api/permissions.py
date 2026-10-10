"""Dispatcher console bootstrap and access-check APIs."""

from __future__ import annotations

import frappe

from dispatch_portal.services.dispatch_access import (
	APP_TITLE,
	DISPATCH_CONSOLE_ROUTE,
	get_dispatch_roles_for_user,
	is_dispatch_user,
	is_verifier,
)

CONSOLE_SECTIONS = (
	{"key": "dashboard", "label": "Dashboard", "icon": "dashboard", "order": 1},
	{"key": "trips", "label": "Trips", "icon": "list", "order": 2},
	{"key": "trip-map", "label": "Trip Map", "icon": "map", "order": 3},
	{"key": "verification", "label": "Verification", "icon": "check", "order": 4},
	{"key": "reports", "label": "Reports", "icon": "chart", "order": 5},
)

DEFAULT_SECTION = "dashboard"


@frappe.whitelist()
def get_console_boot():
	"""Return the console shell configuration for the signed-in dispatcher."""
	permissions = get_dispatch_roles_for_user()
	if not permissions["is_dispatcher"]:
		frappe.throw("You do not have access to the AL RANA Dispatch console.", frappe.PermissionError)

	sections = [dict(section) for section in CONSOLE_SECTIONS]
	if not permissions["is_verifier"]:
		sections = [section for section in sections if section["key"] != "verification"]

	return {
		"app_title": APP_TITLE,
		"route": DISPATCH_CONSOLE_ROUTE,
		"section": DEFAULT_SECTION,
		"sections": sections,
		"permissions": permissions,
	}


@frappe.whitelist()
def has_console_access():
	"""Cheap access probe used by the app launcher icon and page bootstrap."""
	return {
		"has_access": is_dispatch_user(),
		"is_verifier": is_verifier(),
	}
