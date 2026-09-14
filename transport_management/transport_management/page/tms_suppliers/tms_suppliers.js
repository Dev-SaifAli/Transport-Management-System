frappe.pages["tms-suppliers"].on_page_load = function (wrapper) {
	transport_management.make_tms_master_page(wrapper, {
		title: __("Transport Management / Suppliers"),
		master_label: __("ERPNext Supplier master"),
		doctype: "Supplier",
		list_label: __("Open Supplier List"),
		new_label: __("New Supplier"),
	});
};
