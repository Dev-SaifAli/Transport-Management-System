# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from transport_management.location_master import validate_transport_location_usage
from transport_management.tms_billing_setup import TOLL_SERVICE_ITEM, TRANSPORT_SERVICE_ITEM, ensure_tms_billing_setup
from transport_management.transport_management.doctype.transport_charge_rule.transport_charge_rule import (
	get_transport_trip_charge_totals,
)

TON_UOM = "TON"
VAT_RATE = 5
BILLING_STATUS_NOT_READY = "Not Ready"
BILLING_STATUS_READY = "Ready for Billing"
BILLING_STATUS_IN_PROGRESS = "Billing In Progress"
BILLING_STATUS_INVOICED = "Invoiced"
TOLL_INVOICE_TYPE = "Toll / Extra Charges"
TOLL_STATUS_NOT_APPLICABLE = "Not Applicable"
TOLL_STATUS_READY = "Ready for Toll Billing"
TOLL_STATUS_IN_PROGRESS = "Toll Billing In Progress"
TOLL_STATUS_INVOICED = "Toll Invoiced"
BILLING_ROLES = {"Transport Manager", "Transport Admin", "System Manager"}
BILLING_ACTIVE_TRIP_STATUSES = {"PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT"}
BILLING_READY_TRIP_STATUS = "CLOSED"


class TransportJob(Document):
	def before_validate(self):
		if not self.uom:
			self.uom = TON_UOM
		self.calculate_quantity_progress()
		self.billing_status = evaluate_billing_readiness(self)
		self.toll_billing_status = evaluate_toll_billing_readiness(self)

	def validate(self):
		quantity = flt(self.requested_quantity)
		if not isfinite(quantity) or quantity <= 0:
			frappe.throw(_("Requested Quantity must be greater than zero."))

		if self.loading_site and self.loading_site == self.unloading_site:
			frappe.throw(_("Loading Site and Unloading Site must be different."))

		if self.uom != TON_UOM:
			frappe.throw(_("Transport Job UOM must be TON."))

		validate_transport_location_usage(self.loading_site, {"Loading", "Both"}, _("Loading Site"))
		validate_transport_location_usage(self.unloading_site, {"Unloading", "Both"}, _("Unloading Site"))

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
		fields=["planned_quantity", "loaded_quantity", "delivered_quantity", "status"],
	)
	assigned_quantity = sum(flt(row.planned_quantity, 6) for row in rows)
	loaded_quantity = sum(
		flt(row.loaded_quantity, 6)
		for row in rows
		if row.loaded_quantity and row.status in {"LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"}
	)
	delivered_quantity = sum(
		flt(row.delivered_quantity, 6)
		for row in rows
		if row.delivered_quantity and row.status in {"DELIVERED", "POD_RECEIVED", "CLOSED"}
	)
	return {
		"assigned_quantity": flt(assigned_quantity, 6),
		"loaded_quantity": flt(loaded_quantity, 6),
		"delivered_quantity": flt(delivered_quantity, 6),
	}


def refresh_quantity_progress(transport_job):
	if not transport_job or not frappe.db.exists("Transport Job", transport_job):
		return
	job_ref = frappe.db.get_value("Transport Job", transport_job, ["requested_quantity", "sales_order"], as_dict=True)
	requested_quantity = flt(job_ref.requested_quantity, 6)
	progress = get_quantity_progress(transport_job)
	progress["remaining_quantity"] = flt(requested_quantity - progress["delivered_quantity"], 6)
	progress["billing_status"] = evaluate_billing_readiness(transport_job, progress=progress)
	progress["toll_billing_status"] = evaluate_toll_billing_readiness(transport_job)
	frappe.db.set_value("Transport Job", transport_job, progress, update_modified=False)
	if job_ref.sales_order:
		from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
			refresh_sales_order_billing_progress,
		)

		refresh_sales_order_billing_progress(job_ref.sales_order)


def evaluate_billing_readiness(transport_job, progress=None):
	job_name = transport_job if isinstance(transport_job, str) else transport_job.name
	if not job_name:
		return BILLING_STATUS_NOT_READY

	lifecycle_status = get_job_invoice_lifecycle_billing_status(job_name)
	if lifecycle_status:
		return lifecycle_status

	if progress is None:
		requested_quantity = flt(
			frappe.db.get_value("Transport Job", job_name, "requested_quantity")
			or getattr(transport_job, "requested_quantity", 0),
			6,
		)
		progress = get_quantity_progress(job_name)
		progress["remaining_quantity"] = flt(requested_quantity - progress["delivered_quantity"], 6)

	trips = frappe.get_all(
		"Transport Trip",
		filters={"transport_job": job_name},
		fields=["name", "status", "delivered_quantity"],
	)
	billable_trips = [trip for trip in trips if trip.status != "CANCELLED"]
	if not billable_trips:
		return BILLING_STATUS_NOT_READY

	if any(trip.status in BILLING_ACTIVE_TRIP_STATUSES or trip.status == "EXCEPTION" for trip in billable_trips):
		return BILLING_STATUS_NOT_READY

	if any(trip.status != BILLING_READY_TRIP_STATUS for trip in billable_trips):
		return BILLING_STATUS_NOT_READY

	if flt(progress.get("remaining_quantity"), 6) != 0:
		return BILLING_STATUS_NOT_READY

	return BILLING_STATUS_READY


def get_job_invoice_lifecycle_billing_status(transport_job):
	invoice = get_active_transport_invoice_for_job(transport_job)
	if not invoice:
		return None
	if invoice.docstatus == 0:
		return BILLING_STATUS_IN_PROGRESS
	if invoice.docstatus == 1:
		return BILLING_STATUS_INVOICED
	return None


def get_active_transport_invoice_for_job(transport_job):
	invoice_name = None
	if frappe.get_meta("Transport Job").get_field("transport_sales_invoice"):
		invoice_name = frappe.db.get_value("Transport Job", transport_job, "transport_sales_invoice")

	filters = {
		"transport_job": transport_job,
		"tms_invoice_type": "Transport",
		"docstatus": ["<", 2],
	}
	if invoice_name:
		rows = frappe.get_all(
			"Sales Invoice",
			filters={**filters, "name": invoice_name},
			fields=["name", "docstatus"],
			order_by="creation desc",
			limit=1,
		)
		if rows:
			return rows[0]

	rows = frappe.get_all("Sales Invoice", filters=filters, fields=["name", "docstatus"], order_by="creation desc", limit=1)
	if rows:
		return rows[0]
	return None


def evaluate_toll_billing_readiness(transport_job):
	job_name = transport_job if isinstance(transport_job, str) else transport_job.name
	if not job_name:
		return TOLL_STATUS_NOT_APPLICABLE

	invoice = get_active_toll_invoice_for_job(job_name)
	if invoice:
		if invoice.docstatus == 0:
			return TOLL_STATUS_IN_PROGRESS
		if invoice.docstatus == 1:
			return TOLL_STATUS_INVOICED

	if not job_has_all_billable_trips_closed(job_name):
		return TOLL_STATUS_NOT_APPLICABLE

	if flt(get_toll_charge_total(job_name), 2) <= 0:
		return TOLL_STATUS_NOT_APPLICABLE

	return TOLL_STATUS_READY


def job_has_all_billable_trips_closed(transport_job):
	trips = frappe.get_all(
		"Transport Trip",
		filters={"transport_job": transport_job, "status": ["!=", "CANCELLED"]},
		fields=["name", "status"],
	)
	if not trips:
		return False
	return all(trip.status == BILLING_READY_TRIP_STATUS for trip in trips)


def get_toll_charge_total(transport_job):
	result = frappe.db.sql(
		"""
		select coalesce(sum(charge.amount), 0)
		from `tabTransport Trip Charge` charge
		inner join `tabTransport Trip` trip on trip.name = charge.parent
		where charge.parenttype = 'Transport Trip'
			and charge.parentfield = 'transport_charges'
			and trip.transport_job = %s
			and trip.status = %s
		""",
		(transport_job, BILLING_READY_TRIP_STATUS),
	)
	return flt(result[0][0] if result else 0, 2)


def get_active_toll_invoice_for_job(transport_job):
	invoice_name = None
	if frappe.get_meta("Transport Job").get_field("toll_sales_invoice"):
		invoice_name = frappe.db.get_value("Transport Job", transport_job, "toll_sales_invoice")

	filters = {
		"transport_job": transport_job,
		"tms_invoice_type": TOLL_INVOICE_TYPE,
		"docstatus": ["<", 2],
	}
	if invoice_name:
		rows = frappe.get_all(
			"Sales Invoice",
			filters={**filters, "name": invoice_name},
			fields=["name", "docstatus"],
			order_by="creation desc",
			limit=1,
		)
		if rows:
			return rows[0]

	rows = frappe.get_all("Sales Invoice", filters=filters, fields=["name", "docstatus"], order_by="creation desc", limit=1)
	if rows:
		return rows[0]
	return None


@frappe.whitelist()
def prepare_billing(transport_job):
	if not transport_job or not frappe.db.exists("Transport Job", transport_job):
		frappe.throw(_("Transport Job must exist."))

	if not _user_can_prepare_billing():
		frappe.throw(_("You are not permitted to prepare Transport Job billing."), frappe.PermissionError)

	refresh_quantity_progress(transport_job)
	sales_order = frappe.db.get_value("Transport Job", transport_job, "sales_order")
	if not sales_order:
		frappe.throw(_("Transport Job {0} is not linked to a Transport Sales Order.").format(transport_job))

	from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
		prepare_billing as prepare_sales_order_billing,
	)

	result = prepare_sales_order_billing(sales_order)

	return {
		"transport_job": transport_job,
		"transport_sales_order": sales_order,
		"billing_status": result.get("billing_status"),
		"route": "tms-billing-review",
		"message": _("Opening Billing Review for Transport Sales Order {0}.").format(sales_order),
	}


@frappe.whitelist()
def prepare_toll_billing(transport_job):
	if not transport_job or not frappe.db.exists("Transport Job", transport_job):
		frappe.throw(_("Transport Job must exist."))

	if not _user_can_prepare_billing():
		frappe.throw(_("You are not permitted to prepare Toll / Extra Charges billing."), frappe.PermissionError)

	refresh_quantity_progress(transport_job)
	toll_billing_status = frappe.db.get_value("Transport Job", transport_job, "toll_billing_status")
	if toll_billing_status != TOLL_STATUS_READY:
		frappe.throw(_("Transport Job {0} is not ready for Toll / Extra Charges billing.").format(transport_job))

	return {
		"transport_job": transport_job,
		"toll_billing_status": toll_billing_status,
		"route": "tms-toll-billing-review",
		"message": _("Opening Toll Billing Review for Transport Job {0}.").format(transport_job),
	}


def _user_can_prepare_billing(user=None):
	user = user or frappe.session.user
	return bool(BILLING_ROLES.intersection(frappe.get_roles(user)))


@frappe.whitelist()
def get_billing_review(transport_sales_order=None, transport_job=None):
	sales_order = get_sales_order_for_transport_billing(transport_sales_order, transport_job)

	if not _user_can_prepare_billing():
		frappe.throw(_("You are not permitted to review Transport Sales Order billing."), frappe.PermissionError)

	from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
		refresh_sales_order_billing_progress,
	)

	refresh_sales_order_billing_progress(sales_order)
	order = frappe.get_doc("Transport Sales Order", sales_order)
	if order.billing_status not in {BILLING_STATUS_READY, BILLING_STATUS_IN_PROGRESS}:
		frappe.throw(_("Transport Sales Order {0} is not ready for billing.").format(sales_order))

	jobs = get_sales_order_billing_jobs(sales_order)
	trips = get_sales_order_billable_trips(sales_order)
	rows = [build_sales_order_billing_trip_row(trip) for trip in trips]
	groups = group_sales_order_invoice_trips(trips) if trips else []
	return {
		"summary": build_sales_order_billing_summary(order, jobs),
		"jobs": [build_sales_order_job_review_row(job) for job in jobs],
		"trips": rows,
		"groups": [build_billing_group_row(group) for group in groups],
		"totals": calculate_billing_totals(rows),
		"vat_rate": VAT_RATE,
	}


def get_sales_order_for_transport_billing(transport_sales_order=None, transport_job=None):
	if transport_sales_order:
		if not frappe.db.exists("Transport Sales Order", transport_sales_order):
			frappe.throw(_("Transport Sales Order must exist."))
		return transport_sales_order
	if transport_job:
		sales_order = frappe.db.get_value("Transport Job", transport_job, "sales_order")
		if sales_order:
			return sales_order
		frappe.throw(_("Transport Job {0} is not linked to a Transport Sales Order.").format(transport_job))
	frappe.throw(_("Transport Sales Order is required."))


@frappe.whitelist()
def get_toll_billing_review(transport_job):
	if not transport_job or not frappe.db.exists("Transport Job", transport_job):
		frappe.throw(_("Transport Job must exist."))

	if not _user_can_prepare_billing():
		frappe.throw(_("You are not permitted to review Toll / Extra Charges billing."), frappe.PermissionError)

	refresh_quantity_progress(transport_job)
	job = frappe.get_doc("Transport Job", transport_job)
	if job.toll_billing_status not in {TOLL_STATUS_READY, TOLL_STATUS_IN_PROGRESS, TOLL_STATUS_INVOICED}:
		frappe.throw(_("Transport Job {0} is not ready for Toll / Extra Charges billing.").format(transport_job))

	charges = get_toll_source_charges(job.name)
	groups = group_toll_charges(charges)
	return {
		"summary": build_toll_billing_summary(job),
		"charges": [build_toll_charge_review_row(row) for row in charges],
		"groups": [build_toll_group_review_row(row) for row in groups],
		"totals": calculate_toll_totals(groups),
	}


def build_billing_summary(job):
	existing_invoices = get_transport_billing_invoice_summary(job.name)
	active_invoice = get_active_transport_invoice_for_job(job.name)
	return {
		"transport_job": job.name,
		"customer": job.customer,
		"sale_order_reference": job.sale_order_reference,
		"customer_lpo_number": job.customer_lpo_number,
		"material": job.material,
		"loading_site": job.loading_site,
		"unloading_site": job.unloading_site,
		"ordered_quantity": flt(job.requested_quantity, 6),
		"delivered_quantity": flt(job.delivered_quantity, 6),
		"remaining_quantity": flt(job.remaining_quantity, 6),
		"agreed_rate": flt(job.agreed_rate, 2),
		"billing_status": job.billing_status,
		"transport_sales_invoice": job.transport_sales_invoice or (active_invoice.name if active_invoice else None),
		"total_trips": frappe.db.count("Transport Trip", {"transport_job": job.name, "status": BILLING_READY_TRIP_STATUS}),
		"existing_invoices": existing_invoices,
	}


def build_sales_order_billing_summary(order, jobs):
	active_invoice = get_active_transport_invoice_for_sales_order(order.name)
	return {
		"transport_sales_order": order.name,
		"customer": order.customer,
		"posting_date": order.posting_date,
		"customer_lpo_number": order.customer_lpo_number,
		"ordered_quantity": flt(order.ordered_quantity, 6),
		"delivered_quantity": flt(order.delivered_quantity, 6),
		"billing_status": order.billing_status,
		"transport_sales_invoice": order.transport_sales_invoice or (active_invoice.name if active_invoice else None),
		"linked_jobs_count": len(jobs),
		"closed_trips_count": frappe.db.count(
			"Transport Trip",
			{"transport_job": ["in", [job.name for job in jobs]], "status": BILLING_READY_TRIP_STATUS},
		)
		if jobs
		else 0,
		"existing_invoices": get_sales_order_transport_invoice_summary(order.name),
	}


def build_sales_order_job_review_row(job):
	return {
		"transport_job": job.name,
		"sales_order_item": job.sales_order_item,
		"material": job.material,
		"loading_site": job.loading_site,
		"unloading_site": job.unloading_site,
		"ordered_quantity": flt(job.requested_quantity, 6),
		"delivered_quantity": flt(job.delivered_quantity, 6),
		"remaining_quantity": flt(job.remaining_quantity, 6),
		"status": job.status,
	}


def get_sales_order_transport_invoice_summary(sales_order):
	rows = frappe.get_all(
		"Sales Invoice",
		filters={
			"transport_sales_order": sales_order,
			"tms_invoice_type": "Transport",
			"docstatus": ["<", 2],
		},
		fields=["name", "docstatus"],
	)
	return [
		{
			"invoice": row.name,
			"status": get_invoice_status_label(row.docstatus),
			"trips": frappe.db.count("Transport Trip", {"sales_order": sales_order, "status": BILLING_READY_TRIP_STATUS})
			if frappe.get_meta("Transport Trip").get_field("sales_order")
			else count_sales_order_closed_trips(sales_order),
		}
		for row in rows
	]


def count_sales_order_closed_trips(sales_order):
	result = frappe.db.sql(
		"""
		select count(*)
		from `tabTransport Trip` trip
		inner join `tabTransport Job` job on job.name = trip.transport_job
		where job.sales_order = %s
			and trip.status = %s
		""",
		(sales_order, BILLING_READY_TRIP_STATUS),
	)
	return result[0][0] if result else 0


def get_active_transport_invoice_for_sales_order(sales_order):
	invoice_name = frappe.db.get_value("Transport Sales Order", sales_order, "transport_sales_invoice")
	filters = {
		"transport_sales_order": sales_order,
		"tms_invoice_type": "Transport",
		"docstatus": ["<", 2],
	}
	if invoice_name:
		rows = frappe.get_all(
			"Sales Invoice",
			filters={**filters, "name": invoice_name},
			fields=["name", "docstatus"],
			order_by="creation desc",
			limit=1,
		)
		if rows:
			return rows[0]
	rows = frappe.get_all("Sales Invoice", filters=filters, fields=["name", "docstatus"], order_by="creation desc", limit=1)
	return rows[0] if rows else None


def get_legacy_active_transport_invoices_for_sales_order(sales_order):
	jobs = frappe.get_all("Transport Job", filters={"sales_order": sales_order}, pluck="name")
	if not jobs:
		return []
	return frappe.get_all(
		"Sales Invoice",
		filters={
			"transport_job": ["in", jobs],
			"transport_sales_order": ["in", ["", None]],
			"tms_invoice_type": "Transport",
			"docstatus": ["<", 2],
		},
		fields=["name", "transport_job", "docstatus"],
		order_by="creation desc",
	)


def get_sales_order_billing_jobs(sales_order):
	return frappe.get_all(
		"Transport Job",
		filters={"sales_order": sales_order, "status": ["!=", "Cancelled"]},
		fields=[
			"name",
			"sales_order_item",
			"material",
			"loading_site",
			"unloading_site",
			"requested_quantity",
			"delivered_quantity",
			"remaining_quantity",
			"status",
			"agreed_rate",
			"ordered_amount",
		],
		order_by="creation asc",
	)


def build_toll_billing_summary(job):
	active_invoice = get_active_toll_invoice_for_job(job.name)
	return {
		"transport_job": job.name,
		"customer": job.customer,
		"sale_order_reference": job.sale_order_reference,
		"transport_sales_order": job.sales_order,
		"customer_lpo_number": job.customer_lpo_number,
		"job_status": job.status,
		"billing_status": job.billing_status,
		"transport_sales_invoice": job.transport_sales_invoice,
		"toll_billing_status": job.toll_billing_status,
		"toll_sales_invoice": job.toll_sales_invoice or (active_invoice.name if active_invoice else None),
		"total_closed_trips": frappe.db.count("Transport Trip", {"transport_job": job.name, "status": BILLING_READY_TRIP_STATUS}),
		"total_toll_charges": get_toll_charge_total(job.name),
	}


def get_toll_source_charges(transport_job):
	return frappe.db.sql(
		"""
		select
			charge.name as charge_row,
			trip.name as trip,
			trip.trip_date,
			trip.loading_site,
			loading.area_zone as loading_area,
			trip.unloading_site,
			trip.material,
			charge.charge_type,
			charge.charge_rule,
			rule.rule_name as charge_rule_name,
			charge.rate_basis,
			charge.rate,
			charge.quantity,
			charge.amount
		from `tabTransport Trip Charge` charge
		inner join `tabTransport Trip` trip on trip.name = charge.parent
		left join `tabTransport Location` loading on loading.name = trip.loading_site
		left join `tabTransport Charge Rule` rule on rule.name = charge.charge_rule
		where charge.parenttype = 'Transport Trip'
			and charge.parentfield = 'transport_charges'
			and trip.transport_job = %s
			and trip.status = %s
			and coalesce(charge.amount, 0) > 0
		order by trip.trip_date asc, trip.name asc, charge.idx asc
		""",
		(transport_job, BILLING_READY_TRIP_STATUS),
		as_dict=True,
	)


def build_toll_charge_review_row(row):
	return {
		"trip": row.trip,
		"trip_date": row.trip_date,
		"loading_site": row.loading_site,
		"loading_area": row.loading_area,
		"unloading_site": row.unloading_site,
		"material": row.material,
		"charge_type": row.charge_type,
		"charge_rule": row.charge_rule,
		"charge_rule_name": row.charge_rule_name,
		"rate_basis": row.rate_basis,
		"quantity": flt(row.quantity, 6),
		"rate": flt(row.rate, 2),
		"amount": flt(row.amount, 2),
	}


def group_toll_charges(charges):
	groups = {}
	for row in charges:
		description = get_toll_charge_description(row)
		key = (
			description,
			row.charge_type,
			row.loading_site,
			row.loading_area,
			row.unloading_site,
			row.rate_basis,
			flt(row.rate, 2),
			row.material,
			row.charge_rule,
		)
		group = groups.setdefault(
			key,
			{
				"description": description,
				"charge_type": row.charge_type,
				"loading_site": row.loading_site,
				"loading_area": row.loading_area,
				"unloading_site": row.unloading_site,
				"rate_basis": row.rate_basis,
				"rate": flt(row.rate, 2),
				"material": row.material,
				"charge_rule": row.charge_rule,
				"charge_rule_name": row.charge_rule_name,
				"qty": 0,
				"taxable_amount": 0,
				"charge_count": 0,
				"trips": [],
			},
		)
		group["qty"] = flt(group["qty"] + get_toll_group_quantity(row), 6)
		group["taxable_amount"] = flt(group["taxable_amount"] + flt(row.amount, 2), 2)
		group["charge_count"] += 1
		group["trips"].append(row.trip)
	return list(groups.values())


def get_toll_charge_description(row):
	if row.charge_type == "Other" and row.charge_rule_name:
		return row.charge_rule_name.upper()
	return (row.charge_type or "").upper()


def get_toll_group_quantity(row):
	if row.rate_basis == "Per TON":
		return flt(row.quantity, 6)
	return 1


def build_toll_group_review_row(group):
	return {
		"description": group["description"],
		"charge_type": group["charge_type"],
		"loading_site": group["loading_site"],
		"loading_area": group["loading_area"],
		"unloading_site": group["unloading_site"],
		"material": group["material"],
		"charge_rule": group["charge_rule"],
		"charge_rule_name": group["charge_rule_name"],
		"rate_basis": group["rate_basis"],
		"qty": group["qty"],
		"rate": group["rate"],
		"taxable_amount": group["taxable_amount"],
		"vat_percent": 0,
		"vat_amount": 0,
		"net_amount": group["taxable_amount"],
		"charge_count": group["charge_count"],
	}


def calculate_toll_totals(groups):
	return {
		"group_count": len(groups),
		"qty": flt(sum(flt(row["qty"], 6) for row in groups), 6),
		"taxable_amount": flt(sum(flt(row["taxable_amount"], 2) for row in groups), 2),
		"vat_amount": 0,
		"net_amount": flt(sum(flt(row["taxable_amount"], 2) for row in groups), 2),
	}


def get_transport_billing_invoice_summary(transport_job):
	rows = frappe.get_all(
		"Sales Invoice",
		filters={
			"transport_job": transport_job,
			"tms_invoice_type": "Transport",
			"docstatus": ["<", 2],
		},
		fields=["name", "docstatus"],
	)
	return [
		{
			"invoice": row.name,
			"status": get_invoice_status_label(row.docstatus),
			"trips": frappe.db.count("Transport Trip", {"transport_job": transport_job, "status": BILLING_READY_TRIP_STATUS}),
		}
		for row in rows
	]


def get_invoice_status_label(docstatus):
	if docstatus == 0:
		return "Draft"
	if docstatus == 1:
		return "Submitted"
	if docstatus == 2:
		return "Cancelled"
	return "Linked"


def get_billable_trips(job):
	return frappe.db.sql(
		"""
		select
			name, trip_date, execution_source, vehicle, hired_vehicle, driver, hired_driver,
			material, loading_site, unloading_site, gdn, loading_no, delivery_datetime, delivered_quantity,
			rak_toll, sharjah_toll, fnrc_extra_charge, transport_billing_status,
			transport_sales_invoice
		from `tabTransport Trip`
		where transport_job = %s
			and status = %s
		order by trip_date asc, name asc
		""",
		(job.name, BILLING_READY_TRIP_STATUS),
		as_dict=True,
	)


def get_sales_order_billable_trips(sales_order):
	return frappe.db.sql(
		"""
		select
			trip.name, trip.trip_date, trip.execution_source, trip.vehicle, trip.hired_vehicle,
			trip.driver, trip.hired_driver, trip.material, trip.loading_site, trip.unloading_site,
			trip.gdn, trip.loading_no, trip.delivery_datetime, trip.delivered_quantity,
			trip.rak_toll, trip.sharjah_toll, trip.fnrc_extra_charge,
			job.name as transport_job, job.sales_order_item, job.agreed_rate
		from `tabTransport Trip` trip
		inner join `tabTransport Job` job on job.name = trip.transport_job
		where job.sales_order = %s
			and job.status != 'Cancelled'
			and trip.status = %s
		order by trip.trip_date asc, trip.name asc
		""",
		(sales_order, BILLING_READY_TRIP_STATUS),
		as_dict=True,
	)


def build_billing_trip_row(job, trip):
	delivered_quantity = flt(trip.delivered_quantity, 6)
	unit_rate = flt(job.agreed_rate, 2)
	amounts = calculate_trip_transport_amount(delivered_quantity, unit_rate)
	warnings = get_billing_trip_warnings(job, trip, delivered_quantity, unit_rate)
	charge_totals = get_transport_trip_charge_totals(trip.name)

	return {
		"selected": 1,
		"trip": trip.name,
		"trip_date": trip.trip_date,
		"gdn_date": trip.delivery_datetime or trip.trip_date,
		"loading_no": trip.loading_no,
		"execution_source": trip.execution_source,
		"vehicle": trip.hired_vehicle if trip.execution_source == "HIRED" else trip.vehicle,
		"driver": trip.hired_driver if trip.execution_source == "HIRED" else trip.driver,
		"material": trip.material,
		"route": format_route(trip.loading_site, trip.unloading_site),
		"gdn": trip.gdn,
		"delivered_quantity": delivered_quantity,
		"unit_rate": unit_rate,
		"taxable_amount": amounts["taxable_amount"],
		"vat_percent": VAT_RATE,
		"vat_amount": amounts["vat_amount"],
		"net_amount": amounts["net_amount"],
		"rak_toll": flt(charge_totals.get("rak_toll", trip.rak_toll), 2),
		"sharjah_toll": flt(charge_totals.get("sharjah_toll", trip.sharjah_toll), 2),
		"fnrc_extra_charge": flt(charge_totals.get("fnrc_extra_charge", trip.fnrc_extra_charge), 2),
		"warnings": warnings,
	}


def build_sales_order_billing_trip_row(trip):
	delivered_quantity = flt(trip.delivered_quantity, 6)
	unit_rate = flt(trip.agreed_rate, 2)
	amounts = calculate_trip_transport_amount(delivered_quantity, unit_rate)
	charge_totals = get_transport_trip_charge_totals(trip.name)
	return {
		"selected": 1,
		"trip": trip.name,
		"transport_job": trip.transport_job,
		"sales_order_item": trip.sales_order_item,
		"trip_date": trip.trip_date,
		"gdn_date": trip.delivery_datetime or trip.trip_date,
		"loading_no": trip.loading_no,
		"execution_source": trip.execution_source,
		"vehicle": trip.hired_vehicle if trip.execution_source == "HIRED" else trip.vehicle,
		"driver": trip.hired_driver if trip.execution_source == "HIRED" else trip.driver,
		"material": trip.material,
		"route": format_route(trip.loading_site, trip.unloading_site),
		"gdn": trip.gdn,
		"delivered_quantity": delivered_quantity,
		"unit_rate": unit_rate,
		"taxable_amount": amounts["taxable_amount"],
		"vat_percent": VAT_RATE,
		"vat_amount": amounts["vat_amount"],
		"net_amount": amounts["net_amount"],
		"rak_toll": flt(charge_totals.get("rak_toll", trip.rak_toll), 2),
		"sharjah_toll": flt(charge_totals.get("sharjah_toll", trip.sharjah_toll), 2),
		"fnrc_extra_charge": flt(charge_totals.get("fnrc_extra_charge", trip.fnrc_extra_charge), 2),
		"warnings": [],
	}


def build_billing_group_row(group):
	amounts = calculate_trip_transport_amount(group["qty"], group["rate"])
	return {
		"description": "{0} - {1} - {2}".format(group["loading_site"], group["unloading_site"], group["material"]),
		"loading_site": group["loading_site"],
		"unloading_site": group["unloading_site"],
		"material": group["material"],
		"trip_count": len(group["trip_names"]),
		"job_names": group.get("job_names", []),
		"qty": group["qty"],
		"rate": group["rate"],
		"taxable_amount": amounts["taxable_amount"],
		"vat_percent": VAT_RATE,
		"vat_amount": amounts["vat_amount"],
		"net_amount": amounts["net_amount"],
	}


def group_sales_order_invoice_trips(trips):
	groups = {}
	for trip in trips:
		rate = flt(trip.agreed_rate, 2)
		if rate <= 0:
			frappe.throw(_("Transport Job {0} is missing Agreed Rate.").format(trip.transport_job))
		key = (trip.material, trip.loading_site, trip.unloading_site, rate)
		group = groups.setdefault(
			key,
			{
				"material": trip.material,
				"loading_site": trip.loading_site,
				"unloading_site": trip.unloading_site,
				"rate": rate,
				"qty": 0,
				"trip_names": [],
				"job_names": set(),
			},
		)
		group["qty"] = flt(group["qty"] + flt(trip.delivered_quantity, 6), 6)
		group["trip_names"].append(trip.name)
		group["job_names"].add(trip.transport_job)
	for group in groups.values():
		group["job_names"] = sorted(group["job_names"])
	return list(groups.values())


def calculate_trip_transport_amount(delivered_quantity, unit_rate):
	taxable_amount = flt(flt(delivered_quantity, 6) * flt(unit_rate, 2), 2)
	vat_amount = flt(taxable_amount * VAT_RATE / 100, 2)
	net_amount = flt(taxable_amount + vat_amount, 2)
	return {
		"taxable_amount": taxable_amount,
		"vat_amount": vat_amount,
		"net_amount": net_amount,
	}


def calculate_billing_totals(rows):
	selected_rows = [row for row in rows if row.get("selected")]
	return {
		"selected_trips": len(selected_rows),
		"delivered_quantity": flt(sum(flt(row.get("delivered_quantity"), 6) for row in selected_rows), 6),
		"taxable_amount": flt(sum(flt(row.get("taxable_amount"), 2) for row in selected_rows), 2),
		"vat_percent": VAT_RATE,
		"vat_amount": flt(sum(flt(row.get("vat_amount"), 2) for row in selected_rows), 2),
		"net_amount": flt(sum(flt(row.get("net_amount"), 2) for row in selected_rows), 2),
		"rak_toll": flt(sum(flt(row.get("rak_toll"), 2) for row in selected_rows), 2),
		"sharjah_toll": flt(sum(flt(row.get("sharjah_toll"), 2) for row in selected_rows), 2),
		"fnrc_extra_charge": flt(sum(flt(row.get("fnrc_extra_charge"), 2) for row in selected_rows), 2),
	}


def get_billing_trip_warnings(job, trip, delivered_quantity, unit_rate):
	warnings = []
	if delivered_quantity <= 0:
		warnings.append(_("Closed Trip has Delivered Quantity less than or equal to zero."))
	if unit_rate <= 0:
		warnings.append(_("Transport Job is missing Agreed Rate."))
	if not trip.gdn:
		warnings.append(_("Trip is missing GDN / Delivery Reference."))
	if not (trip.hired_vehicle if trip.execution_source == "HIRED" else trip.vehicle):
		warnings.append(_("Trip is missing vehicle."))
	if trip.material != job.material:
		warnings.append(_("Trip material differs from Transport Job material."))
	if trip.loading_site != job.loading_site or trip.unloading_site != job.unloading_site:
		warnings.append(_("Trip route differs from Transport Job route."))
	return warnings


def format_route(loading_site, unloading_site):
	if loading_site and unloading_site:
		return "{0} -> {1}".format(loading_site, unloading_site)
	return loading_site or unloading_site or ""


@frappe.whitelist()
def create_transport_invoice(transport_sales_order=None, transport_job=None, trip_names=None):
	if not _user_can_prepare_billing():
		frappe.throw(_("You are not permitted to create Transport Invoices."), frappe.PermissionError)

	ensure_tms_billing_setup()
	sales_order = get_sales_order_for_transport_billing(transport_sales_order, transport_job)
	from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
		refresh_sales_order_billing_progress,
	)

	refresh_sales_order_billing_progress(sales_order)
	order = frappe.get_doc("Transport Sales Order", sales_order)
	existing_invoice = get_active_transport_invoice_for_sales_order(order.name)
	if existing_invoice:
		frappe.throw(_("Transport Invoice {0} already exists for Sales Order {1}.").format(existing_invoice.name, order.name))
	legacy_invoices = get_legacy_active_transport_invoices_for_sales_order(order.name)
	if legacy_invoices:
		frappe.throw(
			_("Existing Job-level Transport Invoice {0} is active for Sales Order {1}. Resolve the legacy invoice before creating a consolidated Transport Invoice.").format(
				legacy_invoices[0].name, order.name
			)
		)
	if order.billing_status != BILLING_STATUS_READY:
		frappe.throw(_("Transport Sales Order {0} is not ready for billing.").format(order.name))

	company = get_default_company()
	validate_company_currency(company)
	service_item = get_transport_service_item()
	tax_template = get_sales_vat_template(company)
	income_account = get_income_account(company, service_item)
	cost_center = get_cost_center(company)

	trips = get_sales_order_billable_trips(order.name)
	if not trips:
		frappe.throw(_("No CLOSED Trips are available for Transport Sales Order {0}.").format(order.name))
	groups = group_sales_order_invoice_trips(trips)
	jobs = get_sales_order_billing_jobs(order.name)
	invoice = build_transport_sales_order_invoice(
		order=order,
		jobs=jobs,
		company=company,
		service_item=service_item,
		tax_template=tax_template,
		income_account=income_account,
		cost_center=cost_center,
		groups=groups,
	)
	invoice.insert(ignore_permissions=True)
	validate_invoice_totals(invoice, groups)
	mark_trips_draft_invoiced([trip.name for trip in trips], invoice.name)
	frappe.db.set_value(
		"Transport Sales Order",
		order.name,
		{"transport_sales_invoice": invoice.name, "billing_status": BILLING_STATUS_IN_PROGRESS},
		update_modified=False,
	)
	return {
		"invoice": invoice.name,
		"transport_sales_order": order.name,
		"trip_count": len(trips),
		"route": ["Form", "Sales Invoice", invoice.name],
	}


@frappe.whitelist()
def create_toll_invoice(transport_job):
	if not _user_can_prepare_billing():
		frappe.throw(_("You are not permitted to create Toll / Extra Charges Invoices."), frappe.PermissionError)

	ensure_tms_billing_setup()
	refresh_quantity_progress(transport_job)
	job = frappe.get_doc("Transport Job", transport_job)
	existing_invoice = get_active_toll_invoice_for_job(job.name)
	if existing_invoice:
		frappe.throw(
			_("Toll / Extra Charges Invoice {0} already exists for Transport Job {1}.").format(
				existing_invoice.name, job.name
			)
		)
	if job.toll_billing_status != TOLL_STATUS_READY:
		frappe.throw(_("Transport Job {0} is not ready for Toll / Extra Charges billing.").format(transport_job))

	company = get_default_company()
	validate_company_currency(company)
	service_item = get_toll_service_item()
	tax_template = get_toll_sales_tax_template(company)
	income_account = get_income_account(company, service_item)
	cost_center = get_cost_center(company)

	charges = get_toll_source_charges(job.name)
	if not charges:
		frappe.throw(_("No stored Toll / Extra Charge rows are available for Transport Job {0}.").format(job.name))
	groups = group_toll_charges(charges)
	invoice = build_toll_sales_invoice(
		job=job,
		company=company,
		service_item=service_item,
		tax_template=tax_template,
		income_account=income_account,
		cost_center=cost_center,
		groups=groups,
	)
	invoice.insert(ignore_permissions=True)
	validate_toll_invoice_totals(invoice, groups)
	frappe.db.set_value(
		"Transport Job",
		job.name,
		{"toll_sales_invoice": invoice.name, "toll_billing_status": TOLL_STATUS_IN_PROGRESS},
		update_modified=False,
	)
	return {
		"invoice": invoice.name,
		"transport_job": job.name,
		"group_count": len(groups),
		"route": ["Form", "Sales Invoice", invoice.name],
	}


def get_default_company():
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		return company
	companies = frappe.get_all("Company", pluck="name", limit=1)
	if not companies:
		frappe.throw(_("No ERPNext Company is configured. Configure Company before creating a Transport Invoice."))
	return companies[0]


def validate_company_currency(company):
	currency = frappe.db.get_value("Company", company, "default_currency")
	if currency != "AED":
		frappe.throw(_("Company {0} currency must be AED for Transport Invoice creation.").format(company))


def get_transport_service_item():
	if not frappe.db.exists("Item", TRANSPORT_SERVICE_ITEM):
		frappe.throw(
			_("Transport Service Item is not available. Configure the ERPNext Item {0} before creating the invoice.").format(
				TRANSPORT_SERVICE_ITEM
			)
		)
	item = frappe.get_doc("Item", TRANSPORT_SERVICE_ITEM)
	if item.disabled:
		frappe.throw(_("Transport Service Item is disabled."))
	if item.is_stock_item:
		frappe.throw(_("Transport Service Item must be a non-stock service Item."))
	return item.name


def get_toll_service_item():
	if not frappe.db.exists("Item", TOLL_SERVICE_ITEM):
		frappe.throw(
			_("Toll / Extra Charges Item is not available. Configure the ERPNext Item {0} before creating the invoice.").format(
				TOLL_SERVICE_ITEM
			)
		)
	item = frappe.get_doc("Item", TOLL_SERVICE_ITEM)
	if item.disabled:
		frappe.throw(_("Toll / Extra Charges Item is disabled."))
	if item.is_stock_item:
		frappe.throw(_("Toll / Extra Charges Item must be a non-stock service Item."))
	return item.name


def get_sales_vat_template(company):
	rows = frappe.db.sql(
		"""
		select template.name
		from `tabSales Taxes and Charges Template` template
		inner join `tabSales Taxes and Charges` tax on tax.parent = template.name
		where coalesce(template.disabled, 0) = 0
			and (template.company = %s or coalesce(template.company, '') = '')
			and tax.charge_type = 'On Net Total'
			and tax.rate = %s
			and coalesce(tax.account_head, '') != ''
		order by if(template.company = %s, 0, 1), template.name asc
		limit 1
		""",
		(company, VAT_RATE, company),
		as_dict=True,
	)
	if not rows:
		frappe.throw(
			_("5% Sales VAT configuration is not available. Configure the ERPNext VAT account/tax template before creating the invoice.")
		)
	return rows[0].name


def get_toll_sales_tax_template(company):
	message = _("Toll / Extra Charge tax configuration is not available. Configure the applicable ERPNext tax template before creating the Toll Invoice.")
	if not frappe.db.exists("DocType", "TMS Billing Settings"):
		frappe.throw(message)

	template = frappe.db.get_single_value("TMS Billing Settings", "toll_sales_taxes_and_charges_template")
	if not template:
		frappe.throw(message)

	row = frappe.db.get_value(
		"Sales Taxes and Charges Template",
		template,
		["name", "disabled", "company"],
		as_dict=True,
	)
	if not row or row.disabled or (row.company and row.company != company):
		frappe.throw(message)

	tax_rows = frappe.get_all(
		"Sales Taxes and Charges",
		filters={"parent": template},
		fields=["rate"],
	)
	if any(flt(tax.rate, 6) != 0 for tax in tax_rows):
		frappe.throw(message)
	return template


def get_income_account(company, item_code):
	item_default = frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		"income_account",
	)
	account = item_default
	if not account and frappe.get_meta("Company").get_field("default_income_account"):
		account = frappe.db.get_value("Company", company, "default_income_account")
	if account:
		return account
	rows = frappe.get_all(
		"Account",
		filters={"company": company, "root_type": "Income", "is_group": 0, "disabled": 0},
		pluck="name",
		limit=1,
	)
	if not rows:
		frappe.throw(_("Income Account is not configured for company {0}.").format(company))
	return rows[0]


def get_cost_center(company):
	return frappe.db.get_value("Company", company, "cost_center")


def get_selected_invoice_trips(job, trip_names):
	trips = frappe.get_all(
		"Transport Trip",
		filters={"name": ["in", trip_names]},
		fields=[
			"name",
			"transport_job",
			"status",
			"material",
			"loading_site",
			"unloading_site",
			"delivered_quantity",
			"transport_billing_status",
			"transport_sales_invoice",
		],
	)
	found_names = {trip.name for trip in trips}
	missing = [name for name in trip_names if name not in found_names]
	if missing:
		frappe.throw(_("Trip {0} was not found.").format(missing[0]))

	for trip in trips:
		if trip.transport_job != job.name:
			frappe.throw(_("Trip {0} does not belong to Transport Job {1}.").format(trip.name, job.name))
		if trip.status != BILLING_READY_TRIP_STATUS:
			frappe.throw(_("Trip {0} must be CLOSED before creating a Transport Invoice.").format(trip.name))
		if trip.transport_sales_invoice or trip.transport_billing_status in {"Draft Invoice", "Invoiced"}:
			frappe.throw(
				_("Trip {0} is already included in Sales Invoice {1}.").format(
					trip.name, trip.transport_sales_invoice or _("another invoice")
				)
			)
		if flt(trip.delivered_quantity, 6) <= 0:
			frappe.throw(_("Trip {0} has no billable Delivered Quantity.").format(trip.name))
	return trips


def group_invoice_trips(job, trips):
	groups = {}
	for trip in trips:
		rate = flt(trip.get("unit_rate") or trip.get("rate") or job.agreed_rate, 2)
		if rate <= 0:
			frappe.throw(_("Transport Job {0} is missing Agreed Rate.").format(job.name))
		key = (trip.material, trip.loading_site, trip.unloading_site, rate)
		group = groups.setdefault(
			key,
			{
				"material": trip.material,
				"loading_site": trip.loading_site,
				"unloading_site": trip.unloading_site,
				"rate": rate,
				"qty": 0,
				"trip_names": [],
			},
		)
		group["qty"] = flt(group["qty"] + flt(trip.delivered_quantity, 6), 6)
		group["trip_names"].append(trip.name)
	return list(groups.values())


def build_transport_sales_order_invoice(order, jobs, company, service_item, tax_template, income_account, cost_center, groups):
	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = order.customer
	invoice.company = company
	invoice.posting_date = today()
	invoice.currency = "AED"
	invoice.taxes_and_charges = tax_template
	invoice.transport_sales_order = order.name
	invoice.customer_lpo_number = order.customer_lpo_number
	invoice.tms_invoice_type = "Transport"
	for job in jobs:
		invoice.append(
			"tms_source_jobs",
			{
				"transport_job": job.name,
				"sales_order_item": job.sales_order_item,
				"material": job.material,
				"loading_location": job.loading_site,
				"unloading_location": job.unloading_site,
				"delivered_quantity": flt(job.delivered_quantity, 6),
				"amount": flt(flt(job.delivered_quantity, 6) * flt(job.agreed_rate, 2), 2),
			},
		)
	for group in groups:
		description = "{0} - {1} - {2}".format(group["loading_site"], group["unloading_site"], group["material"])
		row = {
			"item_code": service_item,
			"item_name": service_item,
			"description": description,
			"qty": group["qty"],
			"uom": TON_UOM,
			"conversion_factor": 1,
			"rate": group["rate"],
			"income_account": income_account,
			"tms_loading_location": group["loading_site"],
			"tms_unloading_location": group["unloading_site"],
			"tms_material": group["material"],
			"tms_route_description": description,
		}
		if len(group["job_names"]) == 1:
			row["tms_transport_job"] = group["job_names"][0]
		if cost_center:
			row["cost_center"] = cost_center
		invoice.append("items", row)
	append_sales_taxes_from_template(invoice, tax_template)
	return invoice


def build_transport_sales_invoice(job, company, service_item, tax_template, income_account, cost_center, groups):
	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = job.customer
	invoice.company = company
	invoice.posting_date = today()
	invoice.currency = "AED"
	invoice.taxes_and_charges = tax_template
	invoice.transport_job = job.name
	invoice.transport_sales_order = job.sales_order
	invoice.customer_lpo_number = job.customer_lpo_number
	invoice.tms_invoice_type = "Transport"
	for group in groups:
		description = "{0} - {1} - {2}".format(group["loading_site"], group["unloading_site"], group["material"])
		row = {
			"item_code": service_item,
			"item_name": service_item,
			"description": description,
			"qty": group["qty"],
			"uom": TON_UOM,
			"conversion_factor": 1,
			"rate": group["rate"],
			"income_account": income_account,
			"tms_loading_location": group["loading_site"],
			"tms_unloading_location": group["unloading_site"],
			"tms_material": group["material"],
			"tms_transport_job": job.name,
			"tms_route_description": description,
		}
		if cost_center:
			row["cost_center"] = cost_center
		invoice.append("items", row)
	append_sales_taxes_from_template(invoice, tax_template)
	return invoice


def build_toll_sales_invoice(job, company, service_item, tax_template, income_account, cost_center, groups):
	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = job.customer
	invoice.company = company
	invoice.posting_date = today()
	invoice.currency = "AED"
	invoice.taxes_and_charges = tax_template
	invoice.transport_job = job.name
	invoice.transport_sales_order = job.sales_order
	invoice.customer_lpo_number = job.customer_lpo_number
	invoice.tms_invoice_type = TOLL_INVOICE_TYPE
	for group in groups:
		row = {
			"item_code": service_item,
			"item_name": service_item,
			"description": group["description"],
			"qty": group["qty"],
			"uom": "Nos" if frappe.db.exists("UOM", "Nos") else TON_UOM,
			"conversion_factor": 1,
			"rate": group["rate"],
			"income_account": income_account,
			"tms_charge_type": group["description"],
			"tms_loading_location": group["loading_site"],
			"tms_loading_area": group["loading_area"],
			"tms_unloading_location": group["unloading_site"],
			"tms_material": group["material"],
			"tms_rate_basis": group["rate_basis"],
			"tms_transport_job": job.name,
			"tms_charge_rule": group["charge_rule"],
			"tms_route_description": "{0} - {1}".format(group["loading_site"] or "", group["unloading_site"] or ""),
		}
		if cost_center:
			row["cost_center"] = cost_center
		invoice.append("items", row)
	append_sales_taxes_from_template(invoice, tax_template)
	return invoice


def append_sales_taxes_from_template(invoice, tax_template):
	for tax in frappe.get_all(
		"Sales Taxes and Charges",
		filters={"parent": tax_template},
		fields=["charge_type", "account_head", "description", "rate", "cost_center"],
		order_by="idx asc",
	):
		invoice.append("taxes", tax)


def validate_invoice_totals(invoice, groups):
	invoice.run_method("calculate_taxes_and_totals")
	expected_subtotal = flt(sum(flt(group["qty"], 6) * flt(group["rate"], 2) for group in groups), 2)
	if flt(invoice.net_total, 2) != expected_subtotal:
		frappe.throw(_("Invoice subtotal does not match selected Trip taxable amounts."))
	expected_vat = flt(expected_subtotal * VAT_RATE / 100, 2)
	if flt(invoice.total_taxes_and_charges, 2) != expected_vat:
		frappe.throw(_("Invoice VAT does not match configured 5% VAT."))
	expected_grand_total = flt(expected_subtotal + expected_vat, 2)
	if flt(invoice.grand_total, 2) != expected_grand_total:
		frappe.throw(_("Invoice grand total does not match transport subtotal plus VAT."))


def validate_toll_invoice_totals(invoice, groups):
	invoice.run_method("calculate_taxes_and_totals")
	expected_subtotal = flt(sum(flt(group["taxable_amount"], 2) for group in groups), 2)
	if flt(invoice.net_total, 2) != expected_subtotal:
		frappe.throw(_("Toll Invoice subtotal does not match stored charge snapshot amounts."))
	if flt(invoice.total_taxes_and_charges, 2) != 0:
		frappe.throw(_("Toll Invoice tax template must calculate zero VAT for the current configuration."))
	if flt(invoice.grand_total, 2) != expected_subtotal:
		frappe.throw(_("Toll Invoice grand total does not match stored charge snapshot amounts."))


def mark_trips_draft_invoiced(trip_names, invoice):
	for trip in trip_names:
		frappe.db.set_value(
			"Transport Trip",
			trip,
			{
				"transport_billing_status": "Draft Invoice",
				"transport_sales_invoice": invoice,
			},
			update_modified=False,
		)


def sync_transport_invoice_lifecycle(doc, method=None):
	if getattr(doc, "tms_invoice_type", None) not in {"Transport", TOLL_INVOICE_TYPE}:
		return
	if doc.tms_invoice_type == "Transport" and getattr(doc, "transport_sales_order", None):
		sync_sales_order_transport_invoice_lifecycle(doc, method=method)
		return
	if not getattr(doc, "transport_job", None):
		return
	if not frappe.db.exists("Transport Job", doc.transport_job):
		return
	if doc.tms_invoice_type == TOLL_INVOICE_TYPE:
		sync_toll_invoice_lifecycle(doc, method=method)
		return

	if method == "on_trash" or doc.docstatus == 2:
		clear_transport_invoice_reference(doc.transport_job, doc.name)
		refresh_quantity_progress(doc.transport_job)
		return

	if doc.docstatus == 1:
		for trip in get_transport_invoice_trip_names(doc.transport_job, doc.name):
			frappe.db.set_value(
				"Transport Trip",
				trip,
				"transport_billing_status",
				"Invoiced",
				update_modified=False,
			)
		frappe.db.set_value(
			"Transport Job",
			doc.transport_job,
			{"transport_sales_invoice": doc.name, "billing_status": BILLING_STATUS_INVOICED},
			update_modified=False,
		)
		return

	if doc.docstatus == 0:
		frappe.db.set_value(
			"Transport Job",
			doc.transport_job,
			{"transport_sales_invoice": doc.name, "billing_status": BILLING_STATUS_IN_PROGRESS},
			update_modified=False,
		)


def sync_sales_order_transport_invoice_lifecycle(doc, method=None):
	if not frappe.db.exists("Transport Sales Order", doc.transport_sales_order):
		return

	if method == "on_trash" or doc.docstatus == 2:
		clear_sales_order_transport_invoice_reference(doc.transport_sales_order, doc.name)
		from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
			refresh_sales_order_billing_progress,
		)

		refresh_sales_order_billing_progress(doc.transport_sales_order)
		return

	if doc.docstatus == 1:
		for trip in get_sales_order_transport_invoice_trip_names(doc.transport_sales_order, doc.name):
			frappe.db.set_value(
				"Transport Trip",
				trip,
				"transport_billing_status",
				"Invoiced",
				update_modified=False,
			)
		frappe.db.set_value(
			"Transport Sales Order",
			doc.transport_sales_order,
			{"transport_sales_invoice": doc.name, "billing_status": BILLING_STATUS_INVOICED},
			update_modified=False,
		)
		return

	if doc.docstatus == 0:
		frappe.db.set_value(
			"Transport Sales Order",
			doc.transport_sales_order,
			{"transport_sales_invoice": doc.name, "billing_status": BILLING_STATUS_IN_PROGRESS},
			update_modified=False,
		)


def sync_toll_invoice_lifecycle(doc, method=None):
	if method == "on_trash" or doc.docstatus == 2:
		clear_toll_invoice_reference(doc.transport_job, doc.name)
		refresh_quantity_progress(doc.transport_job)
		return

	if doc.docstatus == 1:
		frappe.db.set_value(
			"Transport Job",
			doc.transport_job,
			{"toll_sales_invoice": doc.name, "toll_billing_status": TOLL_STATUS_INVOICED},
			update_modified=False,
		)
		return

	if doc.docstatus == 0:
		frappe.db.set_value(
			"Transport Job",
			doc.transport_job,
			{"toll_sales_invoice": doc.name, "toll_billing_status": TOLL_STATUS_IN_PROGRESS},
			update_modified=False,
		)


def clear_toll_invoice_reference(transport_job, invoice):
	if frappe.db.get_value("Transport Job", transport_job, "toll_sales_invoice") == invoice:
		frappe.db.set_value("Transport Job", transport_job, "toll_sales_invoice", None, update_modified=False)


def clear_transport_invoice_reference(transport_job, invoice):
	for trip in get_transport_invoice_trip_names(transport_job, invoice):
		frappe.db.set_value(
			"Transport Trip",
			trip,
			{
				"transport_billing_status": "Not Billed",
				"transport_sales_invoice": None,
			},
			update_modified=False,
		)
	if frappe.db.get_value("Transport Job", transport_job, "transport_sales_invoice") == invoice:
		frappe.db.set_value("Transport Job", transport_job, "transport_sales_invoice", None, update_modified=False)


def clear_sales_order_transport_invoice_reference(sales_order, invoice):
	for trip in get_sales_order_transport_invoice_trip_names(sales_order, invoice):
		frappe.db.set_value(
			"Transport Trip",
			trip,
			{
				"transport_billing_status": "Not Billed",
				"transport_sales_invoice": None,
			},
			update_modified=False,
		)
	if frappe.db.get_value("Transport Sales Order", sales_order, "transport_sales_invoice") == invoice:
		frappe.db.set_value("Transport Sales Order", sales_order, "transport_sales_invoice", None, update_modified=False)


def get_transport_invoice_trip_names(transport_job, invoice):
	return frappe.get_all(
		"Transport Trip",
		filters={"transport_job": transport_job, "transport_sales_invoice": invoice},
		pluck="name",
	)


def get_sales_order_transport_invoice_trip_names(sales_order, invoice):
	jobs = frappe.get_all("Transport Job", filters={"sales_order": sales_order}, pluck="name")
	if not jobs:
		return []
	return frappe.get_all(
		"Transport Trip",
		filters={"transport_job": ["in", jobs], "transport_sales_invoice": invoice},
		pluck="name",
	)
