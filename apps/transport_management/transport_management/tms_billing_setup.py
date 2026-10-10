"""Billing setup helpers for TMS-owned ERPNext integration fields."""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import cint

TRANSPORT_SERVICE_ITEM = "Transport Service"
TOLL_SERVICE_ITEM = "Toll / Extra Charges"
SALES_INVOICE = "Sales Invoice"
SALES_INVOICE_ITEM = "Sales Invoice Item"
PURCHASE_INVOICE_ITEM = "Purchase Invoice Item"
TMS_TRANSPORT_INVOICE_PRINT_FORMAT = "TMS Transport Invoice"
TMS_TRANSPORT_TRIP_SHEET_PRINT_FORMAT = "TMS Transport Trip Sheet"
TMS_TOLL_INVOICE_PRINT_FORMAT = "TMS Toll / Extra Charges Invoice"
AL_RANA_TOLL_TAX_INVOICE_PRINT_FORMAT = "Toll Tax Invoice - AL RANA"

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
	{
		"fieldname": "tms_transport_billing_section",
		"label": "Transport Billing",
		"fieldtype": "Section Break",
		"insert_after": "tms_source_jobs",
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_billing_from_date",
		"label": "From Date",
		"fieldtype": "Date",
		"insert_after": "tms_transport_billing_section",
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_billing_to_date",
		"label": "To Date",
		"fieldtype": "Date",
		"insert_after": "tms_billing_from_date",
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_get_transport_trips",
		"label": "Get Trips",
		"fieldtype": "Button",
		"insert_after": "tms_billing_to_date",
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_transport_trips",
		"label": "TMS Selected Transport Trips",
		"fieldtype": "Long Text",
		"insert_after": "tms_get_transport_trips",
		"hidden": 1,
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

PURCHASE_INVOICE_ITEM_FIELDS = (
	{
		"fieldname": "tms_transport_trip",
		"label": "Transport Trip",
		"fieldtype": "Link",
		"options": "Transport Trip",
		"insert_after": "description",
		"in_list_view": 1,
		"columns": 2,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_transport_job",
		"label": "Transport Job",
		"fieldtype": "Link",
		"options": "Transport Job",
		"insert_after": "tms_transport_trip",
		"in_list_view": 1,
		"columns": 2,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_transport_sales_order",
		"label": "Transport Sales Order",
		"fieldtype": "Link",
		"options": "Transport Sales Order",
		"insert_after": "tms_transport_job",
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_truck",
		"label": "Truck",
		"fieldtype": "Link",
		"options": "Truck",
		"insert_after": "tms_transport_sales_order",
		"in_list_view": 1,
		"columns": 2,
		"module": "Transport Management",
	},
	{
		"fieldname": "tms_hired_vehicle",
		"label": "Hired Vehicle",
		"fieldtype": "Link",
		"options": "Hired Vehicle",
		"insert_after": "tms_truck",
		"in_list_view": 1,
		"columns": 2,
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

AL_RANA_TOLL_TAX_INVOICE_HTML = """
<style>
	@page { size: A4 portrait; margin: 10mm; }
	.alrana-toll-tax-invoice {
		background: #fff;
		color: #111;
		font-family: Arial, Helvetica, sans-serif;
		font-size: 10.5px;
		line-height: 1.35;
	}
	.alrana-toll-tax-invoice table { border-collapse: collapse; width: 100%; }
	.alrana-toll-tax-invoice .text-center { text-align: center; }
	.alrana-toll-tax-invoice .text-right { text-align: right; }
	.alrana-toll-tax-invoice .title {
		font-size: 15px;
		font-weight: 700;
		margin: 0 0 8px;
		text-align: center;
		text-transform: uppercase;
	}
	.alrana-toll-tax-invoice .header-table { margin-bottom: 8px; }
	.alrana-toll-tax-invoice .header-table td {
		border: 1px solid #222;
		padding: 4px 6px;
		vertical-align: top;
	}
	.alrana-toll-tax-invoice .party-cell { width: 42%; }
	.alrana-toll-tax-invoice .title-cell { text-align: center; width: 16%; }
	.alrana-toll-tax-invoice .party-title {
		font-size: 12px;
		font-weight: 700;
		margin-bottom: 5px;
		text-transform: uppercase;
	}
	.alrana-toll-tax-invoice .meta-line {
		display: grid;
		gap: 4px;
		grid-template-columns: 68px 1fr;
		margin: 1px 0;
	}
	.alrana-toll-tax-invoice .meta-line span { color: #333; }
	.alrana-toll-tax-invoice .meta-line strong { font-weight: 600; }
	.alrana-toll-tax-invoice .items th,
	.alrana-toll-tax-invoice .items td,
	.alrana-toll-tax-invoice .totals-table td {
		border: 1px solid #222;
		padding: 4px 5px;
		vertical-align: top;
	}
	.alrana-toll-tax-invoice .items th {
		background: #f3f3f3;
		font-weight: 700;
		text-align: center;
	}
	.alrana-toll-tax-invoice .items tfoot td { font-weight: 700; }
	.alrana-toll-tax-invoice .description { min-width: 210px; }
	.alrana-toll-tax-invoice .bottom-grid {
		display: grid;
		gap: 10px;
		grid-template-columns: 1fr 220px;
		margin-top: 8px;
	}
	.alrana-toll-tax-invoice .amount-words {
		border: 1px solid #222;
		min-height: 72px;
		padding: 6px;
	}
	.alrana-toll-tax-invoice .tax-note { margin-top: 8px; }
	.alrana-toll-tax-invoice .totals-table td:first-child { font-weight: 700; }
	.alrana-toll-tax-invoice .totals-table td:last-child { text-align: right; }
	@media print {
		.alrana-toll-tax-invoice { font-size: 10px; }
	}
</style>

{% set company_address_doc = frappe.get_doc("Address", doc.company_address) if doc.company_address and frappe.db.exists("Address", doc.company_address) else None %}
{% set customer_address_doc = frappe.get_doc("Address", doc.customer_address) if doc.customer_address and frappe.db.exists("Address", doc.customer_address) else None %}
{% set company_tax_id = doc.company_tax_id or frappe.db.get_value("Company", doc.company, "tax_id") or "" %}
{% set customer_tax_id = doc.tax_id or frappe.db.get_value("Customer", doc.customer, "tax_id") or "" %}
{% set company_phone = company_address_doc.phone if company_address_doc and company_address_doc.phone else "" %}
{% set customer_phone = customer_address_doc.phone if customer_address_doc and customer_address_doc.phone else (doc.contact_mobile or "") %}
{% set company_po_box = company_address_doc.pincode if company_address_doc and company_address_doc.pincode else "" %}
{% set customer_po_box = customer_address_doc.pincode if customer_address_doc and customer_address_doc.pincode else "" %}
{% set currency = doc.currency or "AED" %}
{% set ns = namespace(total_qty=0, total_tax=0) %}

<div class="alrana-toll-tax-invoice">
	<div class="title">{{ _("TAX INVOICE") }}</div>

	<table class="header-table">
		<tr>
			<td class="party-cell">
				<div class="party-title">{{ doc.company or _("AL RANA TRANSPORT LLC") }}</div>
				<div class="meta-line"><span>{{ _("Invoice No") }}</span><strong>{{ doc.name }}</strong></div>
				<div class="meta-line"><span>{{ _("Date") }}</span><strong>{{ frappe.format(doc.posting_date, {"fieldtype": "Date"}) }}</strong></div>
				<div class="meta-line"><span>{{ _("PO No") }}</span><strong>{{ doc.po_no or doc.get("customer_lpo_number") or "" }}</strong></div>
				<div class="meta-line"><span>{{ _("PO Box") }}</span><strong>{{ company_po_box }}</strong></div>
				<div class="meta-line"><span>{{ _("Phone") }}</span><strong>{{ company_phone }}</strong></div>
				<div class="meta-line"><span>{{ _("TRN") }}</span><strong>{{ company_tax_id }}</strong></div>
			</td>
			<td class="title-cell">
				<strong>{{ _("TAX INVOICE") }}</strong>
			</td>
			<td class="party-cell">
				<div class="party-title">{{ doc.customer_name or doc.customer or "" }}</div>
				<div class="meta-line"><span>{{ _("Address") }}</span><strong>{{ doc.address_display or "" }}</strong></div>
				<div class="meta-line"><span>{{ _("PO Box") }}</span><strong>{{ customer_po_box }}</strong></div>
				<div class="meta-line"><span>{{ _("Phone") }}</span><strong>{{ customer_phone }}</strong></div>
				<div class="meta-line"><span>{{ _("TRN") }}</span><strong>{{ customer_tax_id }}</strong></div>
			</td>
		</tr>
	</table>

	<table class="items">
		<thead>
			<tr>
				<th>{{ _("Sr.No") }}</th>
				<th class="description">{{ _("Description") }}</th>
				<th>{{ _("Qty") }}</th>
				<th>{{ _("Unit Price / AED") }}</th>
				<th>{{ _("Taxable Amount") }}</th>
				<th>{{ _("VAT Rate") }}</th>
				<th>{{ _("VAT Amount") }}</th>
				<th>{{ _("AED / Net Amount") }}</th>
			</tr>
		</thead>
		<tbody>
			{% for item in doc.items %}
				{% set taxable = frappe.utils.flt(item.net_amount or item.amount, 2) %}
				{% set row_tax_ratio = (taxable / (doc.net_total or 1)) if doc.net_total else 0 %}
				{% set row_vat = frappe.utils.flt((doc.total_taxes_and_charges or 0) * row_tax_ratio, 2) %}
				{% set row_net = frappe.utils.flt(taxable + row_vat, 2) %}
				{% set row_vat_rate = frappe.utils.flt(row_vat * 100 / taxable, 2) if taxable else 0 %}
				{% set ns.total_qty = ns.total_qty + (item.qty or 0) %}
				{% set ns.total_tax = ns.total_tax + row_vat %}
				<tr>
					<td class="text-center">{{ loop.index }}</td>
					<td>{{ item.get("tms_charge_type") or item.description or item.item_name or item.item_code or "" }}</td>
					<td class="text-right">{{ "%.2f"|format(item.qty or 0) }}</td>
					<td class="text-right">{{ "%.2f"|format(item.rate or 0) }}</td>
					<td class="text-right">{{ "%.2f"|format(taxable) }}</td>
					<td class="text-right">{{ "%.2f"|format(row_vat_rate) }}%</td>
					<td class="text-right">{{ "%.2f"|format(row_vat) }}</td>
					<td class="text-right">{{ "%.2f"|format(row_net) }}</td>
				</tr>
			{% endfor %}
		</tbody>
		<tfoot>
			<tr>
				<td colspan="2" class="text-right">{{ _("Net Total") }}</td>
				<td class="text-right">{{ "%.2f"|format(ns.total_qty) }}</td>
				<td></td>
				<td class="text-right">{{ "%.2f"|format(doc.net_total or 0) }}</td>
				<td></td>
				<td class="text-right">{{ "%.2f"|format(doc.total_taxes_and_charges or ns.total_tax) }}</td>
				<td class="text-right">{{ "%.2f"|format(doc.grand_total or doc.net_total or 0) }}</td>
			</tr>
		</tfoot>
	</table>

	<div class="bottom-grid">
		<div class="amount-words">
			<strong>{{ _("Amount in Words") }}:</strong> {{ doc.in_words or "" }}
			{% if doc.taxes %}
				<div class="tax-note">
					<strong>{{ _("Tax") }}:</strong>
					{% for tax in doc.taxes %}
						{{ tax.description or tax.account_head }} {{ "%.2f"|format(tax.rate or 0) }}% = {{ currency }} {{ "%.2f"|format(tax.tax_amount or 0) }}{% if not loop.last %}, {% endif %}
					{% endfor %}
				</div>
			{% endif %}
		</div>
		<table class="totals-table">
			<tr><td>{{ _("Net Total") }}</td><td>{{ currency }} {{ "%.2f"|format(doc.net_total or 0) }}</td></tr>
			<tr><td>{{ _("Total VAT") }}</td><td>{{ currency }} {{ "%.2f"|format(doc.total_taxes_and_charges or 0) }}</td></tr>
			<tr><td>{{ _("Grand Total") }}</td><td>{{ currency }} {{ "%.2f"|format(doc.grand_total or 0) }}</td></tr>
			<tr><td>{{ _("Outstanding") }}</td><td>{{ currency }} {{ "%.2f"|format(doc.outstanding_amount or 0) }}</td></tr>
		</table>
	</div>
</div>
"""


def ensure_tms_billing_setup():
	ensure_sales_invoice_fields()
	ensure_sales_invoice_item_fields()
	ensure_purchase_invoice_item_fields()
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


def ensure_purchase_invoice_item_fields():
	if not frappe.db.exists("DocType", PURCHASE_INVOICE_ITEM):
		return
	for field in PURCHASE_INVOICE_ITEM_FIELDS:
		ensure_custom_field(PURCHASE_INVOICE_ITEM, field)
	frappe.clear_cache(doctype=PURCHASE_INVOICE_ITEM)


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
	for key in ("label", "options", "insert_after", "read_only", "in_list_view", "columns", "hidden"):
		if key in field:
			updates[key] = cint(field[key]) if key in {"read_only", "in_list_view", "columns", "hidden"} else field[key]
	if updates:
		frappe.db.set_value("Custom Field", custom_field, updates, update_modified=False)


def ensure_transport_invoice_print_format():
	return ensure_print_format(TMS_TRANSPORT_INVOICE_PRINT_FORMAT, TMS_TRANSPORT_INVOICE_HTML)


def ensure_transport_trip_sheet_print_format():
	return ensure_print_format(TMS_TRANSPORT_TRIP_SHEET_PRINT_FORMAT, TMS_TRANSPORT_TRIP_SHEET_HTML)


def ensure_toll_invoice_print_format():
	ensure_print_format(TMS_TOLL_INVOICE_PRINT_FORMAT, TMS_TOLL_INVOICE_HTML)
	return ensure_print_format(AL_RANA_TOLL_TAX_INVOICE_PRINT_FORMAT, AL_RANA_TOLL_TAX_INVOICE_HTML)


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
