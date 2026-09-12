// Copyright (c) 2026, Digital Data Enterprises and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Shipment", {
	transport_order(frm) {
		// Clear the old fetched value when changing orders. Server validation
		// independently enforces the relationship for API/import callers.
		const order = frm.doc.transport_order;
		frm.set_value("customer", "");
		if (order) {
			return frappe.db.get_value("Transportation Order", order, "customer").then((r) => {
				if (frm.doc.transport_order === order) {
					return frm.set_value("customer", r.message?.customer || "");
				}
			});
		}
	},
});
