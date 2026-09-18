frappe.listview_settings["Transport Sales Order"] = {
	add_fields: [
		"customer",
		"customer_lpo_number",
		"ordered_quantity",
		"delivered_quantity",
		"billing_status",
		"transport_sales_invoice",
		"status",
	],

	get_indicator(doc) {
		const status = doc.billing_status || "Not Ready";
		const color = {
			"Not Ready": "gray",
			"Ready for Billing": "orange",
			"Billing In Progress": "blue",
			Invoiced: "green",
		}[status] || "gray";

		return [__(status), color, `billing_status,=,${status}`];
	},

	formatters: {
		customer(value) {
			return text_display(value, "tms-list-customer");
		},

		customer_lpo_number(value) {
			return text_display(value, "tms-list-reference");
		},

		ordered_quantity(value) {
			return quantity_display(value);
		},

		delivered_quantity(value) {
			return quantity_display(value);
		},

		billing_status(value) {
			return status_badge(value, {
				"Not Ready": "gray",
				"Ready for Billing": "orange",
				"Billing In Progress": "blue",
				Invoiced: "green",
			});
		},
	},
};

function quantity_display(value) {
	if (value === undefined || value === null || value === "") {
		return "";
	}
	const number = Number(flt(value, 2)).toLocaleString(undefined, {
		minimumFractionDigits: flt(value, 2) % 1 ? 2 : 0,
		maximumFractionDigits: 2,
	});
	return `<span class="tms-list-qty">${number} TON</span>`;
}

function text_display(value, class_name) {
	const text = value || "";
	const escaped = frappe.utils.escape_html(text);
	return `<span class="${class_name}" title="${escaped}">${escaped}</span>`;
}

function status_badge(value, color_map) {
	const status = value || "";
	const color = color_map[status] || "gray";
	return `<span class="tms-list-badge tms-${color}">${frappe.utils.escape_html(__(status))}</span>`;
}
