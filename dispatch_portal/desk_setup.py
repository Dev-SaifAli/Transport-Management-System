"""Desk registration for the AL RANA Dispatch console.

Registers the ``AL RANA Dispatch`` app launcher icon (Desktop Icon of type
``App``) so it opens ``/app/dispatch-console`` and is role-aware.  Frappe already
creates this icon from the ``add_to_apps_screen`` hook on app install; this module
makes the icon deterministic across reinstalls and keeps its role table and the
exported fixture in sync.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe

from dispatch_portal.services.dispatch_access import (
	APP_NAME,
	APP_TITLE,
	CONSOLE_READ_ROLES,
	DISPATCH_CONSOLE_ROUTE,
)

# Frappe v16 renders the app launcher icon from the SVG files under
# public/icons/desktop_icons/{solid,subtle}/<scrubbed label>.svg and falls back to
# the Desktop Icon `logo_url` when they are not built.
ICON_LOGO_URL = "/assets/dispatch_portal/icons/desktop_icons/solid/al_rana_dispatch.svg"

DESKTOP_ICON_FIXTURE = "desktop_icon/al_rana_dispatch.json"

BODY_BG = "blue"
ICON_TYPE = "App"
LINK_TYPE = "External"

# Desk sorts app launcher icons by `idx`.  The framework app icons sit at 0 and the
# ERPNext module links at 0..101, so a small positive value keeps the dispatcher
# console next to the other app icons instead of inside the module links.
ICON_IDX = 5


def setup_dispatch_console() -> str:
	"""Ensure the app icon exists, points at the console and is role gated."""
	ensure_desktop_icon()
	export_desktop_icon_fixture()
	frappe.clear_cache()
	return "AL RANA Dispatch console registered"


def ensure_desktop_icon() -> None:
	values = {
		"label": APP_TITLE,
		"app": APP_NAME,
		"icon_type": ICON_TYPE,
		"link_type": LINK_TYPE,
		"link": DISPATCH_CONSOLE_ROUTE,
		"logo_url": ICON_LOGO_URL,
		"bg_color": BODY_BG,
		"standard": 1,
		"hidden": 0,
		"idx": ICON_IDX,
	}

	if frappe.db.exists("Desktop Icon", APP_TITLE):
		doc = frappe.get_doc("Desktop Icon", APP_TITLE)
		doc.update(values)
		doc.set("roles", build_role_rows())
		doc.flags.ignore_permissions = True
		doc.flags.ignore_validate = True
		doc.save()
		return

	icon = frappe.new_doc("Desktop Icon")
	icon.update(values)
	icon.set("roles", build_role_rows())
	icon.flags.ignore_permissions = True
	icon.flags.ignore_validate = True
	icon.insert()


def build_role_rows():
	rows = []
	for role in sorted(CONSOLE_READ_ROLES):
		if frappe.db.exists("Role", role):
			rows.append({"role": role})
	return rows


def get_desktop_icon_idx() -> int:
	"""Legacy helper kept for callers that need the dispatch icon position."""
	return ICON_IDX


def export_desktop_icon_fixture() -> None:
	"""Keep the source-controlled fixture in sync with the live document."""
	if not frappe.conf.developer_mode:
		return

	doc = frappe.get_doc("Desktop Icon", APP_TITLE)
	payload = {
		"app": APP_NAME,
		"bg_color": doc.bg_color,
		"doctype": "Desktop Icon",
		"hidden": 0,
		"icon_type": ICON_TYPE,
		"idx": doc.idx,
		"label": APP_TITLE,
		"link": DISPATCH_CONSOLE_ROUTE,
		"link_type": LINK_TYPE,
		"link_to": "",
		"logo_url": ICON_LOGO_URL,
		"name": APP_TITLE,
		"owner": "Administrator",
		"parent_icon": "",
		"restrict_removal": 0,
		"roles": [{"role": row.role} for row in doc.get("roles") or []],
		"standard": 1,
	}

	fixture_path = get_fixture_path()
	fixture_path.parent.mkdir(parents=True, exist_ok=True)
	fixture_path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")


def get_fixture_path() -> Path:
	from dispatch_portal import __file__ as package_file

	return Path(package_file).parent / DESKTOP_ICON_FIXTURE
