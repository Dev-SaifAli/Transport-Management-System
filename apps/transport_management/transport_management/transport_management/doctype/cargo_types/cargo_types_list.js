// Copyright (c) 2026, Digital Data Enterprises and contributors
// For license information, please see license.txt

frappe.listview_settings["Cargo Types"] = {
	onload(listview) {
		// Custom title and primary action for TMS Material master
		listview.page.set_title(__("Materials"));
		listview.page.set_primary_action(__("Add Material"), () => {
			frappe.new_doc("Cargo Types");
		});
	},
	refresh(listview) {
		listview.page.set_title(__("Materials"));
		const $primaryBtn = listview.page.wrapper.find(".primary-action");
		if ($primaryBtn.length) {
			$primaryBtn.text(__("Add Material"));
		}
	},
};

