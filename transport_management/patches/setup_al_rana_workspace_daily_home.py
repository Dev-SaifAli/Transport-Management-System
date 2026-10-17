"""Retired patch entry kept for sites that have not recorded it yet."""

import frappe


def execute():
	"""Do not recreate shortcuts on the retired role-specific workspaces."""
	frappe.clear_cache()
