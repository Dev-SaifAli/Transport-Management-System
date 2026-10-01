frappe.listview_settings["Transport Charge Rule"] = {
	add_fields: [
		"rule_name",
		"loading_area_zone",
		"loading_location",
		"unloading_area_zone",
		"unloading_location",
		"active",
	],

	get_indicator(doc) {
		return [doc.active ? __("Active") : __("Inactive"), doc.active ? "green" : "gray", `active,=,${doc.active ? 1 : 0}`];
	},
};
