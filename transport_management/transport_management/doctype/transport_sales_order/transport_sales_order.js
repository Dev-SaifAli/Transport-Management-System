frappe.ui.form.on("Transport Sales Order", {
	refresh(frm) {
		set_location_queries(frm);
		frm.fields_dict.items.grid.update_docfield_property(
			"manual_rate_override",
			"read_only",
			can_override_rate() ? 0 : 1
		);
		add_billing_actions(frm);
		if (frm.doc.docstatus === 1 && has_unconverted_rows(frm)) {
			frm.add_custom_button(__("Create Transport Job"), () => show_create_jobs_dialog(frm), __("Actions"));
		}
	},

	customer(frm) {
		refresh_item_rates(frm);
	},

	posting_date(frm) {
		refresh_item_rates(frm);
	}
});

frappe.ui.form.on("Transport Sales Order Item", {
	items_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		row.uom = "TON";
		row.manual_rate_override = 0;
		frm.refresh_field("items");
	},

	form_render(frm, cdt, cdn) {
		toggle_rate_editability(frm, locals[cdt][cdn]);
	},

	material(frm, cdt, cdn) {
		refresh_row_rate(frm, locals[cdt][cdn]);
	},

	loading_location(frm, cdt, cdn) {
		refresh_row_rate(frm, locals[cdt][cdn]);
	},

	unloading_location(frm, cdt, cdn) {
		refresh_row_rate(frm, locals[cdt][cdn]);
	},

	quantity(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		row.amount = flt(row.quantity) * flt(row.rate);
		frm.refresh_field("items");
	},

	manual_rate_override(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		toggle_rate_editability(frm, row);
		if (!row.manual_rate_override) {
			row.rate = null;
			row.rate_source = null;
			row.amount = 0;
			refresh_row_rate(frm, row);
		} else {
			row.rate_source = "Manual Override";
		}
		frm.refresh_field("items");
	},

	rate(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.manual_rate_override) {
			refresh_row_rate(frm, row);
			return;
		}
		row.rate_source = "Manual Override";
		row.amount = flt(row.quantity) * flt(row.rate);
		frm.refresh_field("items");
	}
});

function set_location_queries(frm) {
	frm.set_query("loading_location", "items", () => ({
		filters: {
			active: 1,
			location_usage: ["in", ["Loading", "Both"]]
		}
	}));
	frm.set_query("unloading_location", "items", () => ({
		filters: {
			active: 1,
			location_usage: ["in", ["Unloading", "Both"]]
		}
	}));
}

function has_unconverted_rows(frm) {
	return (frm.doc.items || []).some((row) => !row.converted && !row.transport_job);
}

function refresh_item_rates(frm) {
	(frm.doc.items || []).forEach((row) => refresh_row_rate(frm, row));
}

function refresh_row_rate(frm, row) {
	if (row.manual_rate_override) {
		row.rate_source = "Manual Override";
		row.amount = flt(row.quantity) * flt(row.rate);
		frm.refresh_field("items");
		return;
	}
	if (!frm.doc.customer || !frm.doc.posting_date || !row.material || !row.loading_location || !row.unloading_location) {
		return;
	}
	frappe.call({
		method: "transport_management.transport_management.doctype.transport_sales_order.transport_sales_order.get_transport_rate",
		args: {
			customer: frm.doc.customer,
			material: row.material,
			loading_location: row.loading_location,
			unloading_location: row.unloading_location,
			posting_date: frm.doc.posting_date
		},
		callback(response) {
			row.rate = response.message;
			row.rate_source = "Transport Rate";
			row.amount = flt(row.quantity) * flt(row.rate);
			frm.refresh_field("items");
		}
	});
}

function toggle_rate_editability(frm, row) {
	if (!can_override_rate()) {
		frm.fields_dict.items.grid.update_docfield_property("rate", "read_only", 1);
		return;
	}
	const grid_row = frm.fields_dict.items.grid.grid_rows_by_docname[row.name];
	if (!grid_row || !grid_row.grid_form) {
		frm.fields_dict.items.grid.update_docfield_property("rate", "read_only", row.manual_rate_override ? 0 : 1);
		return;
	}
	const rate_field = grid_row.grid_form.fields_dict.rate;
	if (rate_field) {
		rate_field.df.read_only = row.manual_rate_override ? 0 : 1;
		rate_field.refresh();
	}
}

function can_override_rate() {
	return ["Transport Manager", "Transport Admin", "System Manager"].some((role) =>
		frappe.user_roles.includes(role)
	);
}

function can_use_transport_billing() {
	return ["Transport Manager", "Transport Admin", "System Manager"].some((role) =>
		frappe.user_roles.includes(role)
	);
}

function add_billing_actions(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 1 || !can_use_transport_billing()) {
		return;
	}

	if (frm.doc.transport_sales_invoice) {
		frm.add_custom_button(__("Open Transport Invoice"), () => {
			frappe.set_route("Form", "Sales Invoice", frm.doc.transport_sales_invoice);
		}, __("Billing"));
		return;
	}

	if (frm.doc.billing_status === "Ready for Billing") {
		frm.add_custom_button(__("Prepare Billing"), () => {
			frappe.call({
				method:
					"transport_management.transport_management.doctype.transport_sales_order.transport_sales_order.prepare_billing",
				args: {
					sales_order: frm.doc.name
				},
				callback(r) {
					const route = r.message && r.message.route;
					frappe.route_options = { transport_sales_order: frm.doc.name };
					frappe.set_route(route || "tms-billing-review");
				}
			});
		}, __("Billing")).addClass("btn-primary");
	} else if (frm.doc.billing_status === "Billing In Progress") {
		frm.add_custom_button(__("Review Billing"), () => {
			frappe.route_options = { transport_sales_order: frm.doc.name };
			frappe.set_route("tms-billing-review");
		}, __("Billing")).addClass("btn-primary");
	}
}

function show_create_jobs_dialog(frm) {
	const rows = (frm.doc.items || []).filter((row) => !row.converted && !row.transport_job);
	if (!rows.length) {
		frappe.msgprint(__("No unconverted Sales Order rows are available."));
		return;
	}

	const fields = rows.map((row) => ({
		fieldname: row.name,
		fieldtype: "Check",
		label: `${row.idx}. ${row.material} - ${row.loading_location} -> ${row.unloading_location} - ${row.quantity} TON`,
		default: 1
	}));

	const dialog = new frappe.ui.Dialog({
		title: __("Create Transport Jobs"),
		fields,
		primary_action_label: __("Create Jobs"),
		primary_action(values) {
			const selected = rows.filter((row) => values[row.name]).map((row) => row.name);
			if (!selected.length) {
				frappe.msgprint(__("Select at least one row."));
				return;
			}
			frappe.call({
				method: "transport_management.transport_management.doctype.transport_sales_order.transport_sales_order.create_transport_jobs",
				args: {
					sales_order: frm.doc.name,
					row_names: selected
				},
				freeze: true,
				freeze_message: __("Creating Transport Jobs"),
				callback(response) {
					dialog.hide();
					frappe.msgprint(__("Created Transport Jobs: {0}", [(response.message || []).join(", ")]));
					frm.reload_doc();
				}
			});
		}
	});
	dialog.show();
}
