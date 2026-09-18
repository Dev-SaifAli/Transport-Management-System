frappe.listview_settings["Transport Charge Rule"] = {
	add_fields: [
		"rule_name",
		"charge_type",
		"loading_area_zone",
		"loading_location",
		"unloading_location",
		"material",
		"rate_basis",
		"amount",
		"active",
	],

	get_indicator(doc) {
		return [doc.active ? __("Active") : __("Inactive"), doc.active ? "green" : "gray", `active,=,${doc.active ? 1 : 0}`];
	},
};
