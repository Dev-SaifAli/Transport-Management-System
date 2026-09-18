"""Billing setup helpers for TMS-owned ERPNext integration fields."""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import cint

TRANSPORT_SERVICE_ITEM = "Transport Service"
TOLL_SERVICE_ITEM = "Toll / Extra Charges"
SALES_INVOICE = "Sales Invoice"
SALES_INVOICE_ITEM = "Sales Invoice Item"
TMS_TRANSPORT_INVOICE_PRINT_FORMAT = "TMS Transport Invoice"
TMS_TRANSPORT_TRIP_SHEET_PRINT_FORMAT = "TMS Transport Trip Sheet"
TMS_TOLL_INVOICE_PRINT_FORMAT = "TMS Toll / Extra Charges Invoice"

SALES_INVOICE_FIELDS = (
	{
		"fieldname": "transport_job",
		"label": "Transport Job",
		"fieldtype": "Link",
		"options": "Transport Job",
		"insert_after": "customer",
		"read_only": 1,
		"module": "Transport Management",
	},
	{
		"fieldname": "transport_sales_order",
		"label": "Transport Sales Order",
		"fieldtype": "Link",
		"options": "Transport Sales Order",
		"insert_after": "transport_job",
		"read_only": 1,
		"module": "Transport Management",
	},
	{
		"fieldname": "customer_lpo_number",
		"label": "Customer LPO Number",
		"fieldtype": "Data",
		"insert_after": "transport_sales_order",
		"read_only": 1,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_invoice_type",
		"label": "TMS Invoice Type",
		"fieldtype": "Select",
		"options": "\nTransport\nToll / Extra Charges",
		"insert_after": "customer_lpo_number",
		"read_only": 1,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_source_jobs",
		"label": "TMS Source Jobs",
		"fieldtype": "Table",
		"options": "TMS Invoice Source Job",
		"insert_after": "tms_invoice_type",
		"read_only": 1,
		"module": "Transport Management",
	},
)

SALES_INVOICE_ITEM_FIELDS = (
	{
		"fieldname": "tms_loading_location",
		"label": "Loading Point",
		"fieldtype": "Link",
		"options": "Transport Location",
		"insert_after": "description",
		"read_only": 1,
		"in_list_view": 1,
		"columns": 2,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_unloading_location",
		"label": "Unloading Point",
		"fieldtype": "Link",
		"options": "Transport Location",
		"insert_after": "tms_loading_location",
		"read_only": 1,
		"in_list_view": 1,
		"columns": 2,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_material",
		"label": "Material",
		"fieldtype": "Link",
		"options": "Cargo Types",
		"insert_after": "tms_unloading_location",
		"read_only": 1,
		"in_list_view": 1,
		"columns": 2,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_transport_job",
		"label": "TMS Transport Job",
		"fieldtype": "Link",
		"options": "Transport Job",
		"insert_after": "tms_material",
		"read_only": 1,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_route_description",
		"label": "TMS Route Description",
		"fieldtype": "Data",
		"insert_after": "tms_transport_job",
		"read_only": 1,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_charge_type",
		"label": "TMS Charge Type",
		"fieldtype": "Data",
		"insert_after": "tms_route_description",
		"read_only": 1,
		"in_list_view": 1,
		"columns": 2,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_loading_area",
		"label": "TMS Loading Area",
		"fieldtype": "Data",
		"insert_after": "tms_charge_type",
		"read_only": 1,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_rate_basis",
		"label": "TMS Rate Basis",
		"fieldtype": "Data",
		"insert_after": "tms_loading_area",
		"read_only": 1,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_charge_rule",
		"label": "TMS Charge Rule",
		"fieldtype": "Link",
		"options": "Transport Charge Rule",
		"insert_after": "tms_rate_basis",
		"read_only": 1,
		"module": "Transport Management",
	},
)

TMS_TRANSPORT_INVOICE_HTML = """
<style>
	.tms-transport-invoice { font-size: 11px; color: #111; }
	.tms-transport-invoice h2 { margin: 0 0 12px; font-size: 18px; }
	.tms-transport-invoice .meta { width: 100%; margin-bottom: 14px; }
	.tms-transport-invoice .meta td { padding: 3px 6px; vertical-align: top; }
	.tms-transport-invoice .items { width: 100%; border-collapse: collapse; }
	.tms-transport-invoice .items th,
	.tms-transport-invoice .items td { border: 1px solid #d1d8dd; padding: 5px; vertical-align: top; }
	.tms-transport-invoice .items th { background: #f8f8f8; font-weight: 600; text-align: center; }
	.tms-transport-invoice .text-right { text-align: right; }
	.tms-transport-invoice .totals td { font-weight: 600; }
</style>
<div class="tms-transport-invoice">
	<h2>{{ _("TMS Transport Invoice") }}</h2>
	<table class="meta">
		<tr>
			<td><strong>{{ _("Invoice Number") }}:</strong> {{ doc.name }}</td>
			<td><strong>{{ _("Posting Date") }}:</strong> {{ frappe.format(doc.posting_date, {"fieldtype": "Date"}) }}</td>
			<td><strong>{{ _("Currency") }}:</strong> {{ doc.currency or "AED" }}</td>
		</tr>
		<tr>
			<td><strong>{{ _("Customer") }}:</strong> {{ doc.customer_name or doc.customer }}</td>
			<td><strong>{{ _("Customer LPO Number") }}:</strong> {{ doc.customer_lpo_number or "" }}</td>
			<td><strong>{{ _("Transport Sales Order") }}:</strong> {{ doc.transport_sales_order or "" }}</td>
		</tr>
		<tr>
			<td colspan="3">
				{% set source_jobs = frappe.get_all("TMS Invoice Source Job", filters={"parent": doc.name, "parenttype": "Sales Invoice", "parentfield": "tms_source_jobs"}, pluck="transport_job") %}
				<strong>{{ _("Source Jobs") }}:</strong> {{ source_jobs|join(", ") }}
			</td>
		</tr>
	</table>
	{% set ns = namespace(vat_rate=5, total_qty=0, total_vat=0, total_net=0) %}
	{% if doc.taxes %}
		{% set ns.vat_rate = doc.taxes[0].rate or 5 %}
	{% endif %}
	<table class="items">
		<thead>
			<tr>
				<th>{{ _("Sr.No") }}</th>
				<th>{{ _("Description") }}</th>
				<th>{{ _("QTY") }}</th>
				<th>{{ _("Unit Price/AED") }}</th>
				<th>{{ _("Taxable Amount") }}</th>
				<th>{{ _("VAT Rate") }}</th>
				<th>{{ _("VAT Amount") }}</th>
				<th>{{ _("AED/NET Amount") }}</th>
			</tr>
		</thead>
		<tbody>
			{% for item in doc.items %}
				{% set taxable = item.net_amount or item.amount or 0 %}
				{% set vat_amount = frappe.utils.flt(taxable * ns.vat_rate / 100, 2) %}
				{% set row_net = frappe.utils.flt(taxable + vat_amount, 2) %}
				{% set ns.total_qty = ns.total_qty + (item.qty or 0) %}
				{% set ns.total_vat = ns.total_vat + vat_amount %}
				{% set ns.total_net = ns.total_net + row_net %}
				<tr>
					<td class="text-right">{{ loop.index }}</td>
					<td>{{ item.tms_route_description or item.description or "" }}</td>
					<td class="text-right">{{ "%.2f"|format(item.qty or 0) }}</td>
					<td class="text-right">{{ "%.2f"|format(item.rate or 0) }}</td>
					<td class="text-right">{{ "%.2f"|format(taxable) }}</td>
					<td class="text-right">{{ "%.2f"|format(ns.vat_rate) }}%</td>
					<td class="text-right">{{ "%.2f"|format(vat_amount) }}</td>
					<td class="text-right">{{ "%.2f"|format(row_net) }}</td>
				</tr>
			{% endfor %}
		</tbody>
		<tfoot class="totals">
			<tr>
				<td colspan="2" class="text-right">{{ _("Totals") }}</td>
				<td class="text-right">{{ "%.2f"|format(ns.total_qty) }}</td>
				<td></td>
				<td class="text-right">{{ "%.2f"|format(doc.net_total or 0) }}</td>
				<td></td>
				<td class="text-right">{{ "%.2f"|format(doc.total_taxes_and_charges or ns.total_vat) }}</td>
				<td class="text-right">{{ "%.2f"|format(doc.grand_total or ns.total_net) }}</td>
			</tr>
		</tfoot>
	</table>
	{% set source_jobs = frappe.get_all("TMS Invoice Source Job", filters={"parent": doc.name, "parenttype": "Sales Invoice", "parentfield": "tms_source_jobs"}, pluck="transport_job") %}
	{% if not source_jobs and doc.transport_sales_order %}
		{% set source_jobs = frappe.get_all("Transport Job", filters={"sales_order": doc.transport_sales_order}, pluck="name") %}
	{% endif %}
	{% set linked_trip_count = frappe.db.count("Transport Trip", {"transport_job": ["in", source_jobs], "transport_sales_invoice": doc.name, "status": "CLOSED"}) if source_jobs else 0 %}
	{% set closed_trip_count = frappe.db.count("Transport Trip", {"transport_job": ["in", source_jobs], "status": "CLOSED"}) if source_jobs else 0 %}
	<p><strong>{{ _("Total Trips") }}:</strong> {{ linked_trip_count or closed_trip_count }}</p>
</div>
"""

TMS_TRANSPORT_TRIP_SHEET_HTML = """
<style>
	.tms-trip-sheet { font-size: 10px; color: #111; }
	.tms-trip-sheet h2 { margin: 0 0 12px; font-size: 16px; }
	.tms-trip-sheet table { width: 100%; border-collapse: collapse; }
	.tms-trip-sheet th,
	.tms-trip-sheet td { border: 1px solid #222; padding: 4px; vertical-align: top; }
	.tms-trip-sheet th { font-weight: 600; text-align: center; }
	.tms-trip-sheet .text-right { text-align: right; }
	.tms-trip-sheet .totals td { font-weight: 600; }
</style>
<div class="tms-trip-sheet">
	<h2>{{ _("TMS Transport Trip Sheet") }}</h2>
	<p>
		<strong>{{ _("Invoice") }}:</strong> {{ doc.name }}
		&nbsp; | &nbsp;
		<strong>{{ _("Transport Sales Order") }}:</strong> {{ doc.transport_sales_order or "" }}
		&nbsp; | &nbsp;
		<strong>{{ _("Customer") }}:</strong> {{ doc.customer_name or doc.customer }}
	</p>
	{% set source_jobs = frappe.get_all("TMS Invoice Source Job", filters={"parent": doc.name, "parenttype": "Sales Invoice", "parentfield": "tms_source_jobs"}, pluck="transport_job") %}
	{% if not source_jobs and doc.transport_sales_order %}
		{% set source_jobs = frappe.get_all("Transport Job", filters={"sales_order": doc.transport_sales_order}, pluck="name") %}
	{% endif %}
	{% set trips = frappe.get_all("Transport Trip",
		filters={"transport_job": ["in", source_jobs], "transport_sales_invoice": doc.name, "status": "CLOSED"},
		fields=["name", "transport_job", "gdn", "loading_no", "driver", "hired_driver", "delivery_datetime", "trip_date", "loading_site", "unloading_site", "vehicle", "hired_vehicle", "material", "delivered_quantity", "execution_source"],
		order_by="trip_date asc, name asc") if source_jobs else [] %}
	{% if not trips %}
		{% set trips = frappe.get_all("Transport Trip",
			filters={"transport_job": ["in", source_jobs], "status": "CLOSED"},
			fields=["name", "transport_job", "gdn", "loading_no", "driver", "hired_driver", "delivery_datetime", "trip_date", "loading_site", "unloading_site", "vehicle", "hired_vehicle", "material", "delivered_quantity", "execution_source"],
			order_by="trip_date asc, name asc") if source_jobs else [] %}
	{% endif %}
	{% set ns = namespace(total_qty=0, total_taxable=0, total_vat=0, total_net=0, vat_rate=5) %}
	{% if doc.taxes %}
		{% set ns.vat_rate = doc.taxes[0].rate or 5 %}
	{% endif %}
	<table>
		<thead>
			<tr>
				<th>{{ _("S/N") }}</th>
				<th>{{ _("Transport Job") }}</th>
				<th>{{ _("GDN") }}</th>
				<th>{{ _("Loading No.") }}</th>
				<th>{{ _("Driver") }}</th>
				<th>{{ _("GDN Date") }}</th>
				<th>{{ _("Loading Point") }}</th>
				<th>{{ _("Unloading Point") }}</th>
				<th>{{ _("Description / Route") }}</th>
				<th>{{ _("Vehicle") }}</th>
				<th>{{ _("Material") }}</th>
				<th>{{ _("Quantity") }}</th>
				<th>{{ _("Unit Price") }}</th>
				<th>{{ _("Taxable Amount") }}</th>
				<th>{{ _("VAT %") }}</th>
				<th>{{ _("VAT Amount") }}</th>
				<th>{{ _("Net Amount") }}</th>
			</tr>
		</thead>
		<tbody>
			{% for trip in trips %}
				{% set job_rate = frappe.db.get_value("Transport Job", trip.transport_job, "agreed_rate") or 0 %}
				{% set qty = trip.delivered_quantity or 0 %}
				{% set taxable = frappe.utils.flt(qty * job_rate, 2) %}
				{% set vat_amount = frappe.utils.flt(taxable * ns.vat_rate / 100, 2) %}
				{% set net_amount = frappe.utils.flt(taxable + vat_amount, 2) %}
				{% set ns.total_qty = ns.total_qty + qty %}
				{% set ns.total_taxable = ns.total_taxable + taxable %}
				{% set ns.total_vat = ns.total_vat + vat_amount %}
				{% set ns.total_net = ns.total_net + net_amount %}
				<tr>
					<td class="text-right">{{ loop.index }}</td>
					<td>{{ trip.transport_job or "" }}</td>
					<td>{{ trip.gdn or "" }}</td>
					<td>{{ trip.loading_no or "" }}</td>
					<td>{{ trip.hired_driver if trip.execution_source == "HIRED" else trip.driver }}</td>
					<td>{{ frappe.format(trip.delivery_datetime or trip.trip_date, {"fieldtype": "Date"}) }}</td>
					<td>{{ trip.loading_site or "" }}</td>
					<td>{{ trip.unloading_site or "" }}</td>
					<td>{{ (trip.loading_site or "") ~ " - " ~ (trip.unloading_site or "") ~ " - " ~ (trip.material or "") }}</td>
					<td>{{ trip.hired_vehicle if trip.execution_source == "HIRED" else trip.vehicle }}</td>
					<td>{{ trip.material or "" }}</td>
					<td class="text-right">{{ "%.2f"|format(qty) }}</td>
					<td class="text-right">{{ "%.2f"|format(job_rate or 0) }}</td>
					<td class="text-right">{{ "%.2f"|format(taxable) }}</td>
					<td class="text-right">{{ "%.2f"|format(ns.vat_rate) }}%</td>
					<td class="text-right">{{ "%.2f"|format(vat_amount) }}</td>
					<td class="text-right">{{ "%.2f"|format(net_amount) }}</td>
				</tr>
			{% endfor %}
		</tbody>
		<tfoot class="totals">
			<tr>
				<td colspan="11" class="text-right">{{ _("Totals") }} ({{ trips|length }} {{ _("Trips") }})</td>
				<td class="text-right">{{ "%.2f"|format(ns.total_qty) }}</td>
				<td></td>
				<td class="text-right">{{ "%.2f"|format(doc.net_total or ns.total_taxable) }}</td>
				<td></td>
				<td class="text-right">{{ "%.2f"|format(doc.total_taxes_and_charges or ns.total_vat) }}</td>
				<td class="text-right">{{ "%.2f"|format(doc.grand_total or ns.total_net) }}</td>
			</tr>
		</tfoot>
	</table>
</div>
"""

TMS_TOLL_INVOICE_HTML = """
<style>
	.tms-toll-invoice { font-size: 11px; color: #111; }
	.tms-toll-invoice h2 { margin: 0 0 8px; font-size: 16px; text-align: center; }
	.tms-toll-invoice .company { font-size: 15px; font-weight: 700; margin-bottom: 4px; text-align: center; }
	.tms-toll-invoice .meta { width: 100%; margin: 10px 0 14px; }
	.tms-toll-invoice .meta td { padding: 3px 6px; vertical-align: top; }
	.tms-toll-invoice .items { width: 100%; border-collapse: collapse; }
	.tms-toll-invoice .items th,
	.tms-toll-invoice .items td { border: 1px solid #222; padding: 5px; vertical-align: top; }
	.tms-toll-invoice .items th { background: #f8f8f8; font-weight: 600; text-align: center; }
	.tms-toll-invoice .text-right { text-align: right; }
	.tms-toll-invoice .totals td { font-weight: 600; }
</style>
<div class="tms-toll-invoice">
	<div class="company">{{ doc.company or _("AL RANA TRANSPORT LLC") }}</div>
	<h2>{{ _("TAX INVOICE") }}</h2>
	<table class="meta">
		<tr>
			<td><strong>{{ _("Invoice No.") }}:</strong> {{ doc.name }}</td>
			<td><strong>{{ _("Date") }}:</strong> {{ frappe.format(doc.posting_date, {"fieldtype": "Date"}) }}</td>
			<td><strong>{{ _("Currency") }}:</strong> {{ doc.currency or "AED" }}</td>
		</tr>
		<tr>
			<td><strong>{{ _("Company TRN") }}:</strong> {{ frappe.db.get_value("Company", doc.company, "tax_id") or "" }}</td>
			<td><strong>{{ _("Customer") }}:</strong> {{ doc.customer_name or doc.customer }}</td>
			<td><strong>{{ _("Customer TRN") }}:</strong> {{ frappe.db.get_value("Customer", doc.customer, "tax_id") or "" }}</td>
		</tr>
		<tr>
			<td><strong>{{ _("Transport Job") }}:</strong> {{ doc.transport_job or "" }}</td>
			<td><strong>{{ _("Transport Sales Order") }}:</strong> {{ doc.transport_sales_order or "" }}</td>
			<td><strong>{{ _("Customer LPO") }}:</strong> {{ doc.customer_lpo_number or "" }}</td>
		</tr>
		<tr>
			<td colspan="3"><strong>{{ _("Customer Address") }}:</strong> {{ doc.customer_address or "" }}</td>
		</tr>
	</table>
	{% set ns = namespace(total_qty=0, vat_rate=0) %}
	{% if doc.taxes %}
		{% set ns.vat_rate = doc.taxes[0].rate or 0 %}
	{% endif %}
	<table class="items">
		<thead>
			<tr>
				<th>{{ _("Sr.No") }}</th>
				<th>{{ _("Description") }}</th>
				<th>{{ _("QTY") }}</th>
				<th>{{ _("Unit Price/AED") }}</th>
				<th>{{ _("Taxable Amount") }}</th>
				<th>{{ _("VAT Rate") }}</th>
				<th>{{ _("VAT Amount") }}</th>
				<th>{{ _("AED/NET Amount") }}</th>
			</tr>
		</thead>
		<tbody>
			{% for item in doc.items %}
				{% set taxable = item.net_amount or item.amount or 0 %}
				{% set row_tax_ratio = (taxable / (doc.net_total or 1)) if doc.net_total else 0 %}
				{% set vat_amount = frappe.utils.flt((doc.total_taxes_and_charges or 0) * row_tax_ratio, 2) %}
				{% set row_net = frappe.utils.flt(taxable + vat_amount, 2) %}
				{% set ns.total_qty = ns.total_qty + (item.qty or 0) %}
				<tr>
					<td class="text-right">{{ loop.index }}</td>
					<td>{{ item.tms_charge_type or item.description or "" }}</td>
					<td class="text-right">{{ "%.2f"|format(item.qty or 0) }}</td>
					<td class="text-right">{{ "%.2f"|format(item.rate or 0) }}</td>
					<td class="text-right">{{ "%.2f"|format(taxable) }}</td>
					<td class="text-right">{{ "%.2f"|format(ns.vat_rate) }}%</td>
					<td class="text-right">{{ "%.2f"|format(vat_amount) }}</td>
					<td class="text-right">{{ "%.2f"|format(row_net) }}</td>
				</tr>
			{% endfor %}
		</tbody>
		<tfoot class="totals">
			<tr>
				<td colspan="2" class="text-right">{{ _("Totals") }}</td>
				<td class="text-right">{{ "%.2f"|format(ns.total_qty) }}</td>
				<td></td>
				<td class="text-right">{{ "%.2f"|format(doc.net_total or 0) }}</td>
				<td></td>
				<td class="text-right">{{ "%.2f"|format(doc.total_taxes_and_charges or 0) }}</td>
				<td class="text-right">{{ "%.2f"|format(doc.grand_total or doc.net_total or 0) }}</td>
			</tr>
		</tfoot>
	</table>
</div>
"""


def ensure_tms_billing_setup():
	ensure_sales_invoice_fields()
	ensure_sales_invoice_item_fields()
	ensure_transport_invoice_print_format()
	ensure_transport_trip_sheet_print_format()
	ensure_toll_invoice_print_format()
	ensure_transport_service_item()
	ensure_toll_service_item()
	return "TMS billing setup installed"


def ensure_sales_invoice_fields():
	if not frappe.db.exists("DocType", SALES_INVOICE):
		return
	for field in SALES_INVOICE_FIELDS:
		ensure_custom_field(SALES_INVOICE, field)
	frappe.clear_cache(doctype=SALES_INVOICE)


def ensure_sales_invoice_item_fields():
	if not frappe.db.exists("DocType", SALES_INVOICE_ITEM):
		return
	for field in SALES_INVOICE_ITEM_FIELDS:
		ensure_custom_field(SALES_INVOICE_ITEM, field)
	frappe.clear_cache(doctype=SALES_INVOICE_ITEM)


def ensure_custom_field(doctype, field):
	meta = frappe.get_meta(doctype, cached=False)
	existing = meta.get_field(field["fieldname"])
	if existing:
		if existing.fieldtype != field["fieldtype"]:
			frappe.throw(_("{0}.{1} must be a {2} field.").format(doctype, field["fieldname"], field["fieldtype"]))
		update_existing_custom_field(existing.name, field)
		return
	create_custom_field(doctype, field)
	frappe.clear_cache(doctype=doctype)


def update_existing_custom_field(custom_field, field):
	updates = {}
	for key in ("label", "options", "read_only", "in_list_view", "columns"):
		if key in field:
			updates[key] = cint(field[key]) if key in {"read_only", "in_list_view", "columns"} else field[key]
	if updates:
		frappe.db.set_value("Custom Field", custom_field, updates, update_modified=False)


def ensure_transport_invoice_print_format():
	return ensure_print_format(TMS_TRANSPORT_INVOICE_PRINT_FORMAT, TMS_TRANSPORT_INVOICE_HTML)


def ensure_transport_trip_sheet_print_format():
	return ensure_print_format(TMS_TRANSPORT_TRIP_SHEET_PRINT_FORMAT, TMS_TRANSPORT_TRIP_SHEET_HTML)


def ensure_toll_invoice_print_format():
	return ensure_print_format(TMS_TOLL_INVOICE_PRINT_FORMAT, TMS_TOLL_INVOICE_HTML)


def ensure_print_format(print_format_name, html):
	if not frappe.db.exists("DocType", "Print Format") or not frappe.db.exists("DocType", SALES_INVOICE):
		return

	values = {
		"doc_type": SALES_INVOICE,
		"module": "Transport Management",
		"print_format_type": "Jinja",
		"custom_format": 1,
		"disabled": 0,
		"html": html,
	}
	if frappe.db.exists("Print Format", print_format_name):
		doc = frappe.get_doc("Print Format", print_format_name)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return doc

	doc = frappe.new_doc("Print Format")
	doc.name = print_format_name
	doc.print_format_name = print_format_name
	doc.update(values)
	doc.insert(ignore_permissions=True)
	return doc


def ensure_transport_service_item():
	return ensure_service_item(TRANSPORT_SERVICE_ITEM)


def ensure_toll_service_item():
	return ensure_service_item(TOLL_SERVICE_ITEM)


def ensure_service_item(item_code):
	if not frappe.db.exists("DocType", "Item") or frappe.db.exists("Item", item_code):
		return
	if not frappe.db.exists("Item Group", "Services"):
		return

	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": item_code,
		"item_name": item_code,
		"item_group": "Services",
		"stock_uom": get_service_item_uom(item_code),
		"is_stock_item": 0,
		"disabled": 0,
	})
	item.insert(ignore_permissions=True)


def get_service_item_uom(item_code):
	if item_code == TOLL_SERVICE_ITEM and frappe.db.exists("UOM", "Nos"):
		return "Nos"
	if frappe.db.exists("UOM", "TON"):
		return "TON"
	return "Nos"
