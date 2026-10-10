"""Dispatcher trip map API."""

from __future__ import annotations

import frappe

from dispatch_portal.services.trip_map_service import get_trip_map


@frappe.whitelist()
def get_map_data(filters=None):
	return get_trip_map(filters=filters)


@frappe.whitelist()
def get_map_filters():
	from dispatch_portal.services.trip_map_service import STATUS_GROUPS

	return {
		"status_groups": [
			{"value": key, "label": key.replace("_", " ").title(), "statuses": list(statuses)}
			for key, statuses in STATUS_GROUPS.items()
		]
	}
