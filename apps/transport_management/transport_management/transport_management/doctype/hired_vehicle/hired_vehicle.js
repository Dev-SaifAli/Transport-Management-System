frappe.ui.form.on("Hired Vehicle", {
	refresh(frm) {
		frm.set_query("transporter", () => ({
			filters: {
				is_transporter: 1,
				disabled: 0,
			},
		}));
	},
});
