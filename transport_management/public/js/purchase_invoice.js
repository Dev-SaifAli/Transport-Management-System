frappe.ui.form.on("Purchase Invoice Item", {
	tms_transport_trip(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.tms_transport_trip) {
			return;
		}
		frappe.call({
			method: "transport_management.tms_expense_traceability.get_purchase_invoice_item_tms_defaults",
			args: {
				transport_trip: row.tms_transport_trip,
			},
			callback(r) {
				apply_tms_defaults(cdt, cdn, r.message);
			},
		});
	},

	tms_transport_job(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.tms_transport_job || row.tms_transport_trip) {
			return;
		}
		frappe.call({
			method: "transport_management.tms_expense_traceability.get_purchase_invoice_item_tms_defaults",
			args: {
				transport_job: row.tms_transport_job,
			},
			callback(r) {
				apply_tms_defaults(cdt, cdn, r.message);
			},
		});
	},
});

function apply_tms_defaults(cdt, cdn, defaults) {
	if (!defaults) {
		return;
	}
	for (const [fieldname, value] of Object.entries(defaults)) {
		frappe.model.set_value(cdt, cdn, fieldname, value || "");
	}
}
