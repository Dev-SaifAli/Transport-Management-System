frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		apply_tms_transport_item_grid(frm);
	},

	tms_invoice_type(frm) {
		apply_tms_transport_item_grid(frm);
	},
});

function apply_tms_transport_item_grid(frm) {
	const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
	if (!grid) return;

	const is_transport_invoice = frm.doc.tms_invoice_type === "Transport";
	const is_toll_invoice = frm.doc.tms_invoice_type === "Toll / Extra Charges";
	for (const fieldname of ["tms_loading_location", "tms_unloading_location", "tms_material"]) {
		grid.update_docfield_property(fieldname, "in_list_view", is_transport_invoice ? 1 : 0);
	}
	for (const fieldname of ["tms_charge_type", "tms_rate_basis", "tms_charge_rule"]) {
		grid.update_docfield_property(fieldname, "in_list_view", is_toll_invoice ? 1 : 0);
	}
	grid.update_docfield_property("warehouse", "hidden", is_transport_invoice || is_toll_invoice ? 1 : 0);
	frm.refresh_field("items");
}
