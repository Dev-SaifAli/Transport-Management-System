frappe.ui.form.on("Expense Claim", {
	employee(frm) {
		set_expense_claim_header_defaults(frm);
	},
});

frappe.ui.form.on("Expense Claim Detail", {
	transport_trip(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.transport_trip) {
			return;
		}
		frappe.call({
			method: "transport_management.tms_driver_expense.get_expense_claim_detail_tms_defaults",
			args: {
				transport_trip: row.transport_trip,
			},
			callback(r) {
				apply_tms_expense_defaults(cdt, cdn, r.message);
			},
		});
	},

	transport_job(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.transport_job || row.transport_trip) {
			return;
		}
		frappe.call({
			method: "transport_management.tms_driver_expense.get_expense_claim_detail_tms_defaults",
			args: {
				transport_job: row.transport_job,
			},
			callback(r) {
				apply_tms_expense_defaults(cdt, cdn, r.message);
			},
		});
	},
});

function apply_tms_expense_defaults(cdt, cdn, defaults) {
	if (!defaults) {
		return;
	}

	for (const [fieldname, value] of Object.entries(defaults)) {
		frappe.model.set_value(cdt, cdn, fieldname, value || "");
	}
}

function set_expense_claim_header_defaults(frm) {
	if (!frm.doc.employee) {
		frm.set_value({
			department: "",
			expense_approver: "",
		});
		return;
	}

	frappe.call({
		method: "transport_management.tms_driver_expense.get_expense_claim_header_defaults",
		args: {
			employee: frm.doc.employee,
		},
		callback(r) {
			const defaults = r.message || {};
			frm.set_value({
				department: defaults.department || "",
				expense_approver: defaults.expense_approver || "",
			});
		},
	});
}
