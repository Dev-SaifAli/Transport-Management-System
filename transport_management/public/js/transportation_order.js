frappe.ui.form.on("Transportation Order", {
	refresh(frm) {
		tms_setup_transportation_order_demo_form(frm);

		if (!frm.is_new()) {
			frm.add_custom_button(__("Create Transport Shipment"), () => {
				frappe.new_doc("Transport Shipment", {
					transport_order: frm.doc.name,
					loading_site: frm.doc.cargo_location_city,
					offloading_site: frm.doc.cargo_destination_city,
					material: frm.doc.goods_description,
				});
			});
		}
	},

	onload_post_render(frm) {
		tms_setup_transportation_order_demo_form(frm);
	},
});

function tms_setup_transportation_order_demo_form(frm) {
	const hidden_fields = [
		"consignee_and_shipper_section",
		"border_and_transportation_instruction_section",
		"cargo_information_section",
		"cargo_location_country",
		"cargo_destination_country",
		"transport_type",
		"amended_from",
		"cargo_type",
		"cargo_description",
		"cargo",
		"html1",
		"assign_transport",
		"total_assigned",
		"create_invoice",
		"references_section",
		"version",
	];

	hidden_fields.forEach((fieldname) => {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "hidden", 1);
		}
	});

	if (frm.fields_dict.html1?.$wrapper) {
		frm.fields_dict.html1.$wrapper.empty();
	}
}
