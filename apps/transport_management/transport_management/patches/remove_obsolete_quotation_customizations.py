"""Remove the retired transport quotation customizations."""

import frappe


CUSTOM_FIELDS = (
	"Quotation-customer_approval_attachment",
	"Quotation-customer_approval_date",
	"Quotation-customer_approval_reference",
	"Quotation-customer_approval_section",
	"Quotation-customer_approval_status",
	"Quotation-transport_rate_schedule",
	"Quotation-transport_rates_section",
	"Transport Rate-approval_date",
	"Transport Rate-approval_reference",
	"Transport Rate-approval_status",
	"Transport Rate-source_quotation",
	"Transport Rate-source_quotation_rate_row",
	"Transport Rate-source_transport_quotation",
	"Transport Rate-source_transport_quotation_rate_location",
	"Transport Rate-source_transport_quotation_rate_row",
)

PRINT_FORMATS = (
	"AL RANA Transport Quotation",
	"AL RANA Transport Rate Quotation",
)


def execute():
	for custom_field in CUSTOM_FIELDS:
		frappe.delete_doc_if_exists(
			"Custom Field", custom_field, force=True, delete_permanently=True
		)

	for print_format in PRINT_FORMATS:
		frappe.delete_doc_if_exists(
			"Print Format", print_format, force=True, delete_permanently=True
		)
