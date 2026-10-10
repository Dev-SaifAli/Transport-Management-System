"""Guards that keep the AL RANA Dispatch console installable on a real bench."""

from __future__ import annotations

import frappe

REQUIRED_APPS = ("transport_management",)


def before_install():
	"""Fail early with a clear message when the TMS app is missing."""
	installed = set(frappe.get_installed_apps()) | set(frappe.get_all_apps())
	missing = [app for app in REQUIRED_APPS if app not in installed]
	if missing:
		frappe.throw(
			"AL RANA Dispatch depends on the following apps which are not "
			"available on this bench: {0}".format(", ".join(missing))
		)
