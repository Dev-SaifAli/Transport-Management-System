"""Add native daily-home cards, charts, quick lists, and shortcuts."""

from __future__ import annotations

import frappe


NUMBER_CARDS = [
	{
		"name": "Assigned Trips",
		"label": "Assigned Trips",
		"document_type": "Transport Trip",
		"filters_json": [["Transport Trip", "status", "=", "ASSIGNED"]],
	},
	{
		"name": "In Transit Trips",
		"label": "In Transit Trips",
		"document_type": "Transport Trip",
		"filters_json": [["Transport Trip", "status", "=", "IN_TRANSIT"]],
	},
	{
		"name": "Delivered Trips",
		"label": "Delivered Trips",
		"document_type": "Transport Trip",
		"filters_json": [["Transport Trip", "status", "=", "DELIVERED"]],
	},
	{
		"name": "Open Jobs",
		"label": "Open Jobs",
		"document_type": "Transport Job",
		"filters_json": [["Transport Job", "status", "in", ["Ready", "In Progress"]]],
	},
	{
		"name": "Pending Documents",
		"label": "Pending Documents",
		"document_type": "Transport Trip Document",
		"filters_json": [["Transport Trip Document", "verification_status", "=", "PENDING_REVIEW"]],
	},
	{
		"name": "Draft Expense Claims",
		"label": "Draft Expense Claims",
		"document_type": "Expense Claim",
		"filters_json": [["Expense Claim", "docstatus", "=", 0]],
	},
	{
		"name": "Pending Approval",
		"label": "Pending Approval",
		"document_type": "Expense Claim",
		"filters_json": [["Expense Claim", "approval_status", "=", "Draft"]],
	},
	{
		"name": "Open Employee Advances",
		"label": "Open Employee Advances",
		"document_type": "Employee Advance",
		"filters_json": [
			[
				"Employee Advance",
				"status",
				"not in",
				["Claimed", "Returned", "Cancelled"],
			]
		],
	},
	{
		"name": "Unpaid Sales Invoices",
		"label": "Unpaid Sales Invoices",
		"document_type": "Sales Invoice",
		"filters_json": [["Sales Invoice", "docstatus", "=", 1], ["Sales Invoice", "outstanding_amount", ">", 0]],
	},
	{
		"name": "Draft Sales Invoices",
		"label": "Draft Sales Invoices",
		"document_type": "Sales Invoice",
		"filters_json": [["Sales Invoice", "docstatus", "=", 0]],
	},
	{
		"name": "Draft Purchase Invoices",
		"label": "Draft Purchase Invoices",
		"document_type": "Purchase Invoice",
		"filters_json": [["Purchase Invoice", "docstatus", "=", 0]],
	},
	{
		"name": "Draft Payment Entries",
		"label": "Draft Payment Entries",
		"document_type": "Payment Entry",
		"filters_json": [["Payment Entry", "docstatus", "=", 0]],
	},
	{
		"name": "Active Employees",
		"label": "Active Employees",
		"document_type": "Employee",
		"filters_json": [["Employee", "status", "=", "Active"]],
	},
]

DASHBOARD_CHARTS = [
	{
		"name": "AL RANA Trips by Status",
		"chart_name": "AL RANA Trips by Status",
		"chart_type": "Group By",
		"document_type": "Transport Trip",
		"group_by_based_on": "status",
		"group_by_type": "Count",
		"type": "Donut",
	},
	{
		"name": "AL RANA Expense Claims by Approval Status",
		"chart_name": "AL RANA Expense Claims by Approval Status",
		"chart_type": "Group By",
		"document_type": "Expense Claim",
		"group_by_based_on": "approval_status",
		"group_by_type": "Count",
		"type": "Donut",
	},
	{
		"name": "AL RANA Monthly Sales Invoice Value",
		"chart_name": "AL RANA Monthly Sales Invoice Value",
		"chart_type": "Sum",
		"document_type": "Sales Invoice",
		"based_on": "posting_date",
		"value_based_on": "grand_total",
		"timespan": "Last Year",
		"time_interval": "Monthly",
		"timeseries": 1,
		"type": "Bar",
		"filters_json": [["Sales Invoice", "docstatus", "=", 1]],
	},
]

WORKSPACE_DAILY_HOME = {
	"AL RANA Operations": {
		"number_cards": [
			"In Transit Trips",
			"Open Jobs",
			"Delivered Trips",
			"Pending Documents",
		],
		"charts": ["AL RANA Trips by Status"],
		"quick_lists": [
			{"document_type": "Transport Trip", "label": "Active Trips", "quick_list_filter": [["Transport Trip", "status", "not in", ["CLOSED", "CANCELLED"]]]},
			{"document_type": "Transport Job", "label": "Open Jobs", "quick_list_filter": [["Transport Job", "status", "in", ["Ready", "In Progress"]]]},
		],
		"shortcuts": [
			{"type": "DocType", "link_to": "Transport Trip", "label": "New Trip", "doc_view": "New"},
			{"type": "Page", "link_to": "tms-trip-operations", "label": "Trip Operations"},
			{"type": "DocType", "link_to": "Transport Job", "label": "Transport Jobs", "doc_view": "List"},
			{"type": "DocType", "link_to": "Transport Sales Order", "label": "Transport Sales Orders", "doc_view": "List"},
		],
	},
	"AL RANA Dispatcher": {
		"number_cards": [
			"Assigned Trips",
			"In Transit Trips",
			"Delivered Trips",
			"Pending Documents",
		],
		"charts": ["AL RANA Trips by Status"],
		"quick_lists": [
			{"document_type": "Transport Trip", "label": "Active Trips", "quick_list_filter": [["Transport Trip", "status", "in", ["ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED"]]]},
			{"document_type": "Transport Trip Document", "label": "Pending Documents", "quick_list_filter": [["Transport Trip Document", "verification_status", "=", "PENDING_REVIEW"]]},
		],
		"shortcuts": [
			{"type": "Page", "link_to": "tms-trip-operations", "label": "Trip Operations"},
			{"type": "DocType", "link_to": "Transport Trip", "label": "Trips", "doc_view": "List"},
			{"type": "DocType", "link_to": "Transport Trip Document", "label": "Trip Documents", "doc_view": "List"},
		],
	},
	"AL RANA Expenses": {
		"number_cards": [
			"Draft Expense Claims",
			"Pending Approval",
			"Open Employee Advances",
		],
		"charts": ["AL RANA Expense Claims by Approval Status"],
		"quick_lists": [
			{"document_type": "Expense Claim", "label": "Expense Claims", "quick_list_filter": [["Expense Claim", "docstatus", "<", 2]]},
			{"document_type": "Employee Advance", "label": "Employee Advances", "quick_list_filter": [["Employee Advance", "status", "not in", ["Claimed", "Returned", "Cancelled"]]]},
		],
		"shortcuts": [
			{"type": "DocType", "link_to": "Expense Claim", "label": "New Expense Claim", "doc_view": "New"},
			{"type": "DocType", "link_to": "Employee Advance", "label": "New Employee Advance", "doc_view": "New"},
			{"type": "DocType", "link_to": "Expense Claim", "label": "Pending Expense Claims", "doc_view": "List", "stats_filter": [["Expense Claim", "approval_status", "=", "Draft"]]},
		],
	},
	"AL RANA Finance": {
		"number_cards": [
			"Unpaid Sales Invoices",
			"Draft Sales Invoices",
			"Draft Purchase Invoices",
			"Draft Payment Entries",
		],
		"charts": ["AL RANA Monthly Sales Invoice Value"],
		"quick_lists": [
			{"document_type": "Sales Invoice", "label": "Sales Invoices", "quick_list_filter": [["Sales Invoice", "docstatus", "<", 2]]},
			{"document_type": "Purchase Invoice", "label": "Purchase Invoices", "quick_list_filter": [["Purchase Invoice", "docstatus", "<", 2]]},
			{"document_type": "Payment Entry", "label": "Payment Entries", "quick_list_filter": [["Payment Entry", "docstatus", "<", 2]]},
		],
		"shortcuts": [
			{"type": "DocType", "link_to": "Sales Invoice", "label": "New Sales Invoice", "doc_view": "New"},
			{"type": "DocType", "link_to": "Purchase Invoice", "label": "New Purchase Invoice", "doc_view": "New"},
			{"type": "DocType", "link_to": "Payment Entry", "label": "New Payment Entry", "doc_view": "New"},
			{"type": "Report", "link_to": "Accounts Receivable", "label": "Accounts Receivable"},
			{"type": "Report", "link_to": "Accounts Payable", "label": "Accounts Payable"},
			{"type": "Report", "link_to": "General Ledger", "label": "General Ledger"},
		],
	},
	"AL RANA HR": {
		"number_cards": [
			"Active Employees",
			"Pending Approval",
			"Open Employee Advances",
		],
		"charts": ["AL RANA Expense Claims by Approval Status"],
		"quick_lists": [
			{"document_type": "Employee", "label": "Active Employees", "quick_list_filter": [["Employee", "status", "=", "Active"]]},
			{"document_type": "Expense Claim", "label": "Expense Claims", "quick_list_filter": [["Expense Claim", "docstatus", "<", 2]]},
			{"document_type": "Employee Advance", "label": "Employee Advances", "quick_list_filter": [["Employee Advance", "status", "not in", ["Claimed", "Returned", "Cancelled"]]]},
		],
		"shortcuts": [
			{"type": "DocType", "link_to": "Employee", "label": "Employee", "doc_view": "List"},
			{"type": "DocType", "link_to": "Expense Claim", "label": "Expense Claim", "doc_view": "List"},
			{"type": "DocType", "link_to": "Employee Advance", "label": "Employee Advance", "doc_view": "List"},
			{"type": "DocType", "link_to": "Attendance", "label": "Attendance", "doc_view": "List"},
			{"type": "DocType", "link_to": "Leave Application", "label": "Leave Application", "doc_view": "List"},
		],
	},
	"AL RANA Admin": {
		"number_cards": [],
		"charts": [],
		"quick_lists": [],
		"shortcuts": [
			{"type": "DocType", "link_to": "Transport Charge Rule", "label": "Transport Charge Rules", "doc_view": "List"},
			{"type": "DocType", "link_to": "Transport Rate", "label": "Transport Rates", "doc_view": "List"},
			{"type": "DocType", "link_to": "Transport Location", "label": "Locations", "doc_view": "List"},
			{"type": "DocType", "link_to": "Truck Type", "label": "Truck Types", "doc_view": "List"},
			{"type": "DocType", "link_to": "Cargo Types", "label": "Cargo Types", "doc_view": "List"},
			{"type": "Page", "link_to": "tms-data-import", "label": "TMS Data Import"},
			{"type": "DocType", "link_to": "TMS Billing Settings", "label": "TMS Settings", "doc_view": "List"},
		],
	},
}


def execute():
	ensure_number_cards()
	ensure_dashboard_charts()
	update_workspaces()
	frappe.clear_cache()


def ensure_number_cards():
	for card in NUMBER_CARDS:
		values = {
			"doctype": "Number Card",
			"name": card["name"],
			"label": card["label"],
			"type": "Document Type",
			"document_type": card["document_type"],
			"function": "Count",
			"filters_json": frappe.as_json(card["filters_json"]),
			"is_public": 1,
			"is_standard": 0,
			"module": "",
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily",
		}
		upsert_doc("Number Card", card["name"], values)


def ensure_dashboard_charts():
	for chart in DASHBOARD_CHARTS:
		values = {
			"doctype": "Dashboard Chart",
			"name": chart["name"],
			"chart_name": chart["chart_name"],
			"chart_type": chart["chart_type"],
			"document_type": chart["document_type"],
			"filters_json": frappe.as_json(chart.get("filters_json", [])),
			"is_public": 1,
			"is_standard": 0,
			"module": "",
			"timespan": chart.get("timespan", "Last Year"),
			"time_interval": chart.get("time_interval", "Yearly"),
			"timeseries": chart.get("timeseries", 0),
			"type": chart["type"],
			"group_by_based_on": chart.get("group_by_based_on", ""),
			"group_by_type": chart.get("group_by_type", "Count"),
			"based_on": chart.get("based_on", ""),
			"value_based_on": chart.get("value_based_on", ""),
			"number_of_groups": 0,
		}
		upsert_doc("Dashboard Chart", chart["name"], values)


def upsert_doc(doctype: str, name: str, values: dict):
	is_existing = frappe.db.exists(doctype, name)
	if is_existing:
		doc = frappe.get_doc(doctype, name)
		for field, value in values.items():
			if field != "doctype":
				doc.set(field, value)
	else:
		doc = frappe.get_doc(values)
		doc.set("__islocal", 1)
	doc.flags.ignore_permissions = True
	if not is_existing:
		doc.insert()
	else:
		doc.save()


def update_workspaces():
	for workspace_name, config in WORKSPACE_DAILY_HOME.items():
		if not frappe.db.exists("Workspace", workspace_name):
			continue
		doc = frappe.get_doc("Workspace", workspace_name)
		doc.type = "Workspace"
		set_child_rows(doc, "number_cards", [number_card_row(name) for name in config["number_cards"]])
		set_child_rows(doc, "charts", [chart_row(name) for name in config["charts"]])
		set_child_rows(doc, "quick_lists", [quick_list_row(row) for row in config["quick_lists"]])
		set_child_rows(doc, "shortcuts", [shortcut_row(row) for row in config["shortcuts"]])
		doc.flags.ignore_permissions = True
		doc.save()


def set_child_rows(doc, fieldname: str, rows: list[dict]):
	doc.set(fieldname, [])
	for row in rows:
		doc.append(fieldname, row)


def number_card_row(name: str):
	return {"number_card_name": name, "label": frappe.db.get_value("Number Card", name, "label") or name}


def chart_row(name: str):
	return {"chart_name": name, "label": frappe.db.get_value("Dashboard Chart", name, "chart_name") or name}


def quick_list_row(row: dict):
	return {
		"document_type": row["document_type"],
		"label": row["label"],
		"quick_list_filter": frappe.as_json(row.get("quick_list_filter", [])),
	}


def shortcut_row(row: dict):
	return {
		"type": row["type"],
		"link_to": row["link_to"],
		"label": row["label"],
		"doc_view": row.get("doc_view", ""),
		"stats_filter": frappe.as_json(row.get("stats_filter", [])),
	}
