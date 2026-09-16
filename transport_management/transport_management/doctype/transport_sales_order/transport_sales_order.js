frappe.ui.form.on("Transport Sales Order", {
	refresh(frm) {
		set_location_queries(frm);
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
		frm.refresh_field("items");
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
			row.amount = flt(row.quantity) * flt(row.rate);
			frm.refresh_field("items");
		}
	});
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
