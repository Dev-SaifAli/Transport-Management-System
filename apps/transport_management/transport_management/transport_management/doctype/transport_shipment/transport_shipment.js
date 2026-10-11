// Copyright (c) 2026, Digital Data Enterprises and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Shipment", {
	refresh(frm) {
		frm.dashboard.set_headline(__("Retired legacy record. Use Transport Job and Transport Trip for active TMS work."));
	},
});
