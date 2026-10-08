frappe.ui.form.on("Employee Advance", {
	setup(frm) {
		frm.set_query("advance_account", function () {
			const filters = {
				root_type: "Asset",
				is_group: 0,
				company: frm.doc.company,
				account_currency: frm.doc.currency,
				account_type: "Receivable",
			};

			if (frm.doc.company === "AL RANA TRANSPORT LLC" && frm.tms_employee_advance_account) {
				filters.name = frm.tms_employee_advance_account;
			}

			return { filters };
		});
	},

	onload(frm) {
		apply_al_rana_employee_advance_defaults(frm);
	},

	refresh(frm) {
		apply_al_rana_employee_advance_defaults(frm);
	},

	employee(frm) {
		apply_al_rana_employee_advance_defaults(frm);
	},

	company(frm) {
		apply_al_rana_employee_advance_defaults(frm);
	},
});

function apply_al_rana_employee_advance_defaults(frm) {
	if (!frm.is_new() || (!frm.doc.employee && !frm.doc.company)) {
		return;
	}

	frappe.call({
		method: "transport_management.tms_employee_advance.get_employee_advance_defaults",
		args: {
			employee: frm.doc.employee,
			company: frm.doc.company,
		},
		callback(r) {
			const defaults = r.message || {};
			frm.tms_employee_advance_account = defaults.advance_account || null;

			if (!defaults.company) {
				return;
			}

			const values = {};
			if (!frm.doc.company) {
				values.company = defaults.company;
			}
			if (!frm.doc.currency || frm.doc.currency !== defaults.currency) {
				values.currency = defaults.currency || "";
			}
			if (!frm.doc.advance_account || frm.doc.advance_account !== defaults.advance_account) {
				values.advance_account = defaults.advance_account || "";
			}

			if (Object.keys(values).length) {
				frm.set_value(values);
			}
		},
	});
}
