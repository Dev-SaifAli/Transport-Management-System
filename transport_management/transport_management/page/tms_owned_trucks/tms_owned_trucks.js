frappe.pages["tms-owned-trucks"].on_page_load = function (wrapper) {
	transport_management.make_tms_master_page(wrapper, {
		title: __("Transport Management / Owned Trucks"),
		master_label: __("TMS Truck master"),
		doctype: "Truck",
		list_label: __("Open Truck List"),
		new_label: __("New Truck"),
	});
};
