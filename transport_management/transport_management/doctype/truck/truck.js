frappe.ui.form.on("Truck", {
	setup(frm) {
		frm.set_query("trans_ms_driver", () => ({
			filters: {
				status: "Active",
			},
		}));
	},
});
