frappe.pages["tms-drivers"].on_page_load = function (wrapper) {
	transport_management.make_tms_master_page(wrapper, {
		title: __("Transport Management / Drivers"),
		master_label: __("TMS Truck Driver master"),
		doctype: "Truck Driver",
		list_label: __("Open Driver List"),
		new_label: __("New Driver"),
	});
};
