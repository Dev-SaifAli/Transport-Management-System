frappe.pages["tms-customers"].on_page_load = function (wrapper) {
	transport_management.make_tms_master_page(wrapper, {
		title: __("Transport Management / Customers"),
		master_label: __("ERPNext Customer master"),
		doctype: "Customer",
		list_label: __("Open Customer List"),
		new_label: __("New Customer"),
	});
};
