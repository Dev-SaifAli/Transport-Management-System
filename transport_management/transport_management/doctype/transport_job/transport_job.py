# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from transport_management.location_master import validate_active_transport_locations


class TransportJob(Document):
	def before_validate(self):
		self.calculate_quantity_progress()

	def validate(self):
		quantity = flt(self.requested_quantity)
		if not isfinite(quantity) or quantity <= 0:
			frappe.throw(_("Requested Quantity must be greater than zero."))

		if self.loading_site and self.loading_site == self.unloading_site:
			frappe.throw(_("Loading Site and Unloading Site must be different."))

		validate_active_transport_locations(
			self,
			(("loading_site", _("Loading Site")), ("unloading_site", _("Unloading Site"))),
		)

	def calculate_quantity_progress(self):
		if not self.name:
			self.assigned_quantity = 0
			self.loaded_quantity = 0
			self.delivered_quantity = 0
			self.remaining_quantity = flt(self.requested_quantity, 6)
			return

		progress = get_quantity_progress(self.name)
		self.assigned_quantity = progress["assigned_quantity"]
		self.loaded_quantity = progress["loaded_quantity"]
		self.delivered_quantity = progress["delivered_quantity"]
		self.remaining_quantity = flt(flt(self.requested_quantity, 6) - progress["delivered_quantity"], 6)


def get_quantity_progress(transport_job):
	"""Return progress supported by the current Transport Trip schema."""
	rows = frappe.get_all(
		"Transport Trip",
		filters={"transport_job": transport_job, "status": ["!=", "CANCELLED"]},
		fields=["planned_quantity", "actual_quantity", "status"],
	)
	assigned_quantity = sum(flt(row.planned_quantity, 6) for row in rows)
	loaded_quantity = sum(
		flt(row.actual_quantity or row.planned_quantity, 6)
		for row in rows
		if row.status in {"LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"}
	)
	delivered_quantity = sum(
		flt(row.actual_quantity or row.planned_quantity, 6)
		for row in rows
		if row.status in {"DELIVERED", "POD_RECEIVED", "CLOSED"}
	)
	return {
		"assigned_quantity": flt(assigned_quantity, 6),
		"loaded_quantity": flt(loaded_quantity, 6),
		"delivered_quantity": flt(delivered_quantity, 6),
	}


def refresh_quantity_progress(transport_job):
	if not transport_job or not frappe.db.exists("Transport Job", transport_job):
		return
	requested_quantity = flt(frappe.db.get_value("Transport Job", transport_job, "requested_quantity"), 6)
	progress = get_quantity_progress(transport_job)
	progress["remaining_quantity"] = flt(requested_quantity - progress["delivered_quantity"], 6)
	frappe.db.set_value("Transport Job", transport_job, progress, update_modified=False)
