// Copyright (c) 2026, Digital Data Enterprises and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cargo Types", {
	onload(frm) {
		if (frm.is_new()) {
			const urlParams = new URLSearchParams(window.location.search);
			const prefill = urlParams.get("cargo_name") || frappe.route_options?.cargo_name;
			if (prefill && !frm.doc.cargo_name) {
				frm.set_value("cargo_name", prefill);
			}
		}
	},
	refresh(frm) {
		const title = frm.is_new() ? __("New Material") : (frm.doc.cargo_name || __("Material"));
		frm.page.set_title(title);
	},
});
