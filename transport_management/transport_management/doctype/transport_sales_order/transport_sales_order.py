# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

TON_UOM = "TON"
MANUAL_RATE_OVERRIDE_ROLES = {"Transport Manager", "Transport Admin", "System Manager"}
BILLING_STATUS_NOT_READY = "Not Ready"
BILLING_STATUS_READY = "Ready for Billing"
BILLING_STATUS_IN_PROGRESS = "Billing In Progress"
BILLING_STATUS_INVOICED = "Invoiced"
BILLING_ROLES = {"Transport Manager", "Transport Admin", "System Manager"}
BILLING_READY_TRIP_STATUS = "CLOSED"
BILLING_ACTIVE_TRIP_STATUSES = {"PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT"}


class TransportSalesOrder(Document):
	def before_validate(self):
		if not self.posting_date:
			self.posting_date = today()
		if not self.currency:
			self.currency = "AED"

		self.calculate_totals()
		self.set_conversion_status()
		self.set_billing_progress()

	def validate(self):
		self.validate_customer()
		self.validate_items(require_complete=self.is_submit_action())
		self.calculate_totals(require_rates=self.is_submit_action())
		self.set_conversion_status()
		self.set_billing_progress()

	def before_submit(self):
		self.validate_items(require_complete=True)
		self.calculate_totals(require_rates=True)
		self.status = "Submitted"

	def on_submit(self):
		frappe.db.set_value(self.doctype, self.name, "status", "Submitted", update_modified=False)

	def before_cancel(self):
		active_jobs = get_active_linked_jobs(self.name)
		if active_jobs:
			frappe.throw(
				_("Cannot cancel Sales Order {0} because active Transport Jobs exist: {1}.").format(
					self.name,
					", ".join(active_jobs),
				)
			)

	def on_cancel(self):
		frappe.db.set_value(self.doctype, self.name, "status", "Cancelled", update_modified=False)

	def is_submit_action(self):
		return getattr(self, "_action", None) == "submit" or self.docstatus == 1

	def validate_customer(self):
		if self.customer and not frappe.db.exists("Customer", self.customer):
			frappe.throw(_("Customer {0} does not exist.").format(self.customer))

	def validate_items(self, require_complete=False):
		if require_complete and not self.items:
			frappe.throw(_("Sales Order must have at least one item row."))

		for row in self.items:
			validate_ton_uom(row.uom)
			self.validate_item_row(row, require_complete=require_complete)

	def validate_item_row(self, row, require_complete=False):
		quantity = flt(row.quantity, 6)
		if not isfinite(quantity) or quantity <= 0:
			frappe.throw(_("Quantity must be greater than zero on row {0}.").format(row.idx))

		if require_complete:
			for fieldname, label in (
				("material", _("Item / Material")),
				("loading_location", _("Loading Point")),
				("unloading_location", _("Unloading Point")),
			):
				if not row.get(fieldname):
					frappe.throw(_("{0} is required on row {1}.").format(label, row.idx))

		if row.material:
			validate_active_material(row.material)
		if row.loading_location:
			validate_location_usage(row.loading_location, {"Loading", "Both"}, _("Loading Point"))
		if row.unloading_location:
			validate_location_usage(row.unloading_location, {"Unloading", "Both"}, _("Unloading Point"))
		if row.loading_location and row.loading_location == row.unloading_location:
			frappe.throw(_("Loading Point and Unloading Point must be different on row {0}.").format(row.idx))
		if row.transport_job and not frappe.db.exists("Transport Job", row.transport_job):
			frappe.throw(_("Transport Job {0} linked on row {1} does not exist.").format(row.transport_job, row.idx))
		if row.manual_rate_override:
			validate_manual_rate_override_permission()

	def calculate_totals(self, require_rates=False):
		net_amount = 0
		ordered_quantity = 0
		for row in self.items:
			if not row.uom:
				row.uom = TON_UOM
			validate_ton_uom(row.uom)

			if row.manual_rate_override:
				validate_manual_rate_override_permission()
				validate_manual_rate(row.rate, row.idx)
				row.rate_source = "Manual Override"
			elif self.can_resolve_rate(row):
				row.rate = resolve_transport_rate(
					self.customer,
					row.material,
					row.loading_location,
					row.unloading_location,
					self.posting_date,
					raise_if_missing=require_rates,
				)
				row.rate_source = "Transport Rate" if row.rate else ""
			elif require_rates:
				raise_missing_rate(row, self.customer)

			if require_rates and (row.rate is None or row.rate == ""):
				raise_missing_rate(row, self.customer)

			row.amount = flt(row.quantity, 6) * flt(row.rate, 6)
			net_amount += flt(row.amount, 6)
			ordered_quantity += flt(row.quantity, 6)

		self.net_amount = net_amount
		self.ordered_quantity = ordered_quantity

	def set_billing_progress(self):
		if not self.name:
			self.delivered_quantity = 0
			self.billing_status = BILLING_STATUS_NOT_READY
			return
		self.delivered_quantity = get_sales_order_delivered_quantity(self.name)
		self.billing_status = evaluate_sales_order_billing_status(self.name)

	def can_resolve_rate(self, row):
		return all((
			self.customer,
			self.posting_date,
			row.material,
			row.loading_location,
			row.unloading_location,
		))

	def set_conversion_status(self):
		if self.docstatus == 2:
			self.status = "Cancelled"
			return
		if self.docstatus == 0:
			self.status = "Draft"
			return

		converted = [row for row in self.items if row.converted or row.transport_job]
		if not converted:
			self.status = "Submitted"
		elif len(converted) == len(self.items):
			self.status = "Converted"
		else:
			self.status = "Partially Converted"


@frappe.whitelist()
def get_transport_rate(customer, material, loading_location, unloading_location, posting_date):
	"""Return the active customer/material/route rate for the given order date."""
	return resolve_transport_rate(
		customer,
		material,
		loading_location,
		unloading_location,
		posting_date,
		raise_if_missing=True,
	)


def resolve_transport_rate(
	customer,
	material,
	loading_location,
	unloading_location,
	posting_date,
	raise_if_missing=True,
):
	if not all((customer, material, loading_location, unloading_location, posting_date)):
		frappe.throw(_("Customer, Material, Loading, Unloading, and Date are required to resolve rate."))

	rates = frappe.db.sql(
		"""
		select name, rate
		from `tabTransport Rate`
		where customer = %(customer)s
			and material = %(material)s
			and loading_location = %(loading_location)s
			and unloading_location = %(unloading_location)s
			and active = 1
			and valid_from <= %(posting_date)s
			and (valid_to is null or valid_to = '' or %(posting_date)s <= valid_to)
		order by valid_from desc, creation desc
		""",
		{
			"customer": customer,
			"material": material,
			"loading_location": loading_location,
			"unloading_location": unloading_location,
			"posting_date": getdate(posting_date),
		},
		as_dict=True,
	)

	if len(rates) > 1:
		frappe.throw(_("Multiple active transport rates found for this customer, material, and route."))
	if not rates:
		if not raise_if_missing:
			return None
		frappe.throw(
			_(
				"No active transport rate found for Customer {0}, Material {1}, Loading {2}, Unloading {3}."
			).format(customer, material, loading_location, unloading_location)
		)
	return flt(rates[0].rate, 6)


@frappe.whitelist()
def create_transport_jobs(sales_order, row_names=None):
	"""Create one Transport Job per selected submitted Sales Order row."""
	selected_rows = parse_row_names(row_names)
	doc = frappe.get_doc("Transport Sales Order", sales_order)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Transport Jobs can only be created from a submitted Sales Order."))
	if not frappe.has_permission("Transport Job", "create"):
		frappe.throw(_("You do not have permission to create Transport Jobs."))

	rows = get_rows_for_conversion(doc, selected_rows)
	if not rows:
		frappe.throw(_("No unconverted Sales Order rows were selected."))

	created_jobs = []
	for row in rows:
		created_jobs.append(create_transport_job_from_row(doc, row))

	update_conversion_status(doc.name)
	return created_jobs


def parse_row_names(row_names):
	if not row_names:
		return None
	if isinstance(row_names, str):
		row_names = frappe.parse_json(row_names)
	if isinstance(row_names, str):
		row_names = [row_names]
	return set(row_names)


def get_rows_for_conversion(doc, selected_rows):
	rows = []
	for row in doc.items:
		if selected_rows and row.name not in selected_rows:
			continue
		if row.converted or row.transport_job:
			frappe.throw(_("Sales Order row {0} is already converted.").format(row.idx))
		rows.append(row)
	return rows


def create_transport_job_from_row(doc, row):
	lock_sales_order_item(row.name)
	child_state = frappe.db.get_value(
		"Transport Sales Order Item",
		row.name,
		["converted", "transport_job"],
		as_dict=True,
	)
	if child_state.converted or child_state.transport_job:
		frappe.throw(_("Sales Order row {0} is already converted.").format(row.idx))

	existing_job = frappe.db.get_value(
		"Transport Job",
		{"sales_order": doc.name, "sales_order_item": row.name},
		"name",
	)
	if existing_job:
		frappe.db.set_value(
			"Transport Sales Order Item",
			row.name,
			{"transport_job": existing_job, "converted": 1},
			update_modified=False,
		)
		return existing_job

	job = frappe.new_doc("Transport Job")
	job.update({
		"customer": doc.customer,
		"requested_date": doc.posting_date,
		"loading_site": row.loading_location,
		"unloading_site": row.unloading_location,
		"material": row.material,
		"requested_quantity": row.quantity,
		"uom": TON_UOM,
		"sales_order": doc.name,
		"sales_order_item": row.name,
		"customer_lpo_number": doc.customer_lpo_number,
		"sale_order_reference": doc.name,
		"agreed_rate": row.rate,
		"ordered_amount": row.amount,
		"special_instructions": doc.remarks,
	})
	job.insert()

	frappe.db.set_value(
		"Transport Sales Order Item",
		row.name,
		{"transport_job": job.name, "converted": 1},
		update_modified=False,
	)
	return job.name


def lock_sales_order_item(row_name):
	if not frappe.db.sql(
		"select name from `tabTransport Sales Order Item` where name = %s for update",
		row_name,
	):
		frappe.throw(_("Sales Order row {0} does not exist.").format(row_name))


def update_conversion_status(sales_order):
	doc = frappe.get_doc("Transport Sales Order", sales_order)
	doc.set_conversion_status()
	doc.set_billing_progress()
	frappe.db.set_value(
		"Transport Sales Order",
		sales_order,
		{"status": doc.status, "delivered_quantity": doc.delivered_quantity, "billing_status": doc.billing_status},
		update_modified=False,
	)


def refresh_sales_order_billing_progress(sales_order):
	if not sales_order or not frappe.db.exists("Transport Sales Order", sales_order):
		return
	values = {
		"delivered_quantity": get_sales_order_delivered_quantity(sales_order),
		"billing_status": evaluate_sales_order_billing_status(sales_order),
	}
	frappe.db.set_value("Transport Sales Order", sales_order, values, update_modified=False)


def get_sales_order_delivered_quantity(sales_order):
	result = frappe.db.sql(
		"""
		select coalesce(sum(delivered_quantity), 0)
		from `tabTransport Job`
		where sales_order = %s
			and status != 'Cancelled'
		""",
		(sales_order,),
	)
	return flt(result[0][0] if result else 0, 6)


def evaluate_sales_order_billing_status(sales_order):
	invoice = get_active_transport_invoice_for_sales_order(sales_order)
	if invoice:
		if invoice.docstatus == 0:
			return BILLING_STATUS_IN_PROGRESS
		if invoice.docstatus == 1:
			return BILLING_STATUS_INVOICED

	jobs = get_sales_order_jobs(sales_order)
	if not jobs:
		return BILLING_STATUS_NOT_READY

	for job in jobs:
		if flt(job.remaining_quantity, 6) != 0:
			return BILLING_STATUS_NOT_READY
		if flt(job.delivered_quantity, 6) <= 0:
			return BILLING_STATUS_NOT_READY

	trips = frappe.get_all(
		"Transport Trip",
		filters={"transport_job": ["in", [job.name for job in jobs]], "status": ["!=", "CANCELLED"]},
		fields=["name", "status"],
	)
	if not trips:
		return BILLING_STATUS_NOT_READY
	if any(trip.status in BILLING_ACTIVE_TRIP_STATUSES or trip.status == "EXCEPTION" for trip in trips):
		return BILLING_STATUS_NOT_READY
	if any(trip.status != BILLING_READY_TRIP_STATUS for trip in trips):
		return BILLING_STATUS_NOT_READY

	return BILLING_STATUS_READY


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


def get_sales_order_jobs(sales_order):
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
		],
		order_by="creation asc",
	)


@frappe.whitelist()
def prepare_billing(sales_order):
	if not sales_order or not frappe.db.exists("Transport Sales Order", sales_order):
		frappe.throw(_("Transport Sales Order must exist."))
	if not _user_can_prepare_billing():
		frappe.throw(_("You are not permitted to prepare Transport Sales Order billing."), frappe.PermissionError)
	refresh_sales_order_billing_progress(sales_order)
	billing_status = frappe.db.get_value("Transport Sales Order", sales_order, "billing_status")
	if billing_status != BILLING_STATUS_READY:
		frappe.throw(_("Transport Sales Order {0} is not ready for billing.").format(sales_order))
	return {
		"transport_sales_order": sales_order,
		"billing_status": billing_status,
		"route": "tms-billing-review",
	}


def _user_can_prepare_billing(user=None):
	user = user or frappe.session.user
	return bool(BILLING_ROLES.intersection(frappe.get_roles(user)))


def get_active_linked_jobs(sales_order):
	return frappe.get_all(
		"Transport Job",
		filters={
			"sales_order": sales_order,
			"status": ["!=", "Cancelled"],
		},
		pluck="name",
	)


def validate_ton_uom(uom):
	if uom != TON_UOM:
		frappe.throw(_("UOM must be TON."))


def validate_manual_rate_override_permission():
	if MANUAL_RATE_OVERRIDE_ROLES.intersection(set(frappe.get_roles())):
		return
	frappe.throw(_("You are not permitted to override Transport Rates manually."))


def validate_manual_rate(rate, row_idx):
	rate = flt(rate, 6)
	if not isfinite(rate) or rate <= 0:
		frappe.throw(_("Manual Rate must be greater than zero on row {0}.").format(row_idx))


def validate_active_material(material):
	active = frappe.db.get_value("Cargo Types", material, "active")
	if active is None:
		frappe.throw(_("Material {0} does not exist.").format(material))
	if not active:
		frappe.throw(_("Material {0} must be active.").format(material))


def validate_location_usage(location, allowed_usages, label):
	if not frappe.db.exists("Transport Location", location):
		frappe.throw(_("{0} must be a valid Transport Location.").format(label))

	values = frappe.db.get_value(
		"Transport Location",
		location,
		["location_usage", "active"],
		as_dict=True,
	)
	if not values.active:
		frappe.throw(_("{0} must be an active Transport Location.").format(label))
	if values.location_usage not in allowed_usages:
		frappe.throw(
			_("{0} must have Location Usage {1}.").format(
				label,
				_(" or ").join(sorted(allowed_usages)),
			)
		)


def raise_missing_rate(row, customer):
	frappe.throw(
		_(
			"No active transport rate found for Customer {0}, Material {1}, Loading {2}, Unloading {3}."
		).format(customer, row.material, row.loading_location, row.unloading_location)
	)


def ensure_ton_uom():
	if frappe.db.exists("UOM", TON_UOM):
		return TON_UOM
	uom = frappe.new_doc("UOM")
	uom.uom_name = TON_UOM
	uom.enabled = 1
	uom.insert(ignore_permissions=True)
	return uom.name
