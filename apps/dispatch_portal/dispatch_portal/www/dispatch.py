"""Website controller for the Vue dispatch portal."""

from __future__ import annotations

import json
from urllib.parse import quote

import frappe


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + quote("/dispatch")
		raise frappe.Redirect

	context.no_cache = 1
	context.frappe_boot_json = json.dumps(
		{
			"csrf_token": frappe.sessions.get_csrf_token(),
			"user": frappe.session.user,
			"full_name": frappe.utils.get_fullname(frappe.session.user),
		}
	)
	return context
