"""Website controller for the Vue dispatch portal."""

from __future__ import annotations

import json
from urllib.parse import quote

import frappe
import frappe.sessions


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote("/dispatch")
		raise frappe.Redirect

	context.no_cache = 1
	csrf_token = None
	try:
		csrf_token = frappe.sessions.get_csrf_token()
	except Exception:
		csrf_token = getattr(frappe.local, "session", {}).get("data", {}).get("csrf_token", "")

	context.frappe_boot_json = json.dumps(
		{
			"csrf_token": csrf_token or "",
			"user": frappe.session.user,
			"full_name": frappe.utils.get_fullname(frappe.session.user),
		}
	)
	return context
