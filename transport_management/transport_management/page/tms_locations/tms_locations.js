frappe.pages["tms-locations"].on_page_load = function (wrapper) {
	transport_management.make_tms_master_page(wrapper, {
		title: __("Transport Management / Locations"),
		master_label: __("Fleet Transport Location master"),
		doctype: "Transport Location",
		list_label: __("Open Location List"),
		new_label: __("New Location"),
	});
};
