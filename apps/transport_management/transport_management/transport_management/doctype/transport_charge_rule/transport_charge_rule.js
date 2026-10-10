frappe.ui.form.on("Transport Charge Rule", {
	refresh(frm) {
		set_route_fields_read_only(frm);
		if (frm.is_new() && !frm.doc.rule_name) {
			update_rule_name(frm);
		}
	},

	loading_location(frm) {
		fetch_area_zone(frm, "loading_location", "loading_area_zone");
	},

	unloading_location(frm) {
		fetch_area_zone(frm, "unloading_location", "unloading_area_zone");
	},

	loading_area_zone(frm) {
		update_rule_name(frm);
	},

	unloading_area_zone(frm) {
		update_rule_name(frm);
	},
});

function set_route_fields_read_only(frm) {
	["rule_name", "loading_area_zone", "unloading_area_zone"].forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", 1);
	});
}

function fetch_area_zone(frm, location_field, zone_field) {
	const selected_location = frm.doc[location_field];

	if (!selected_location) {
		frm.set_value(zone_field, "");
		update_rule_name(frm);
		return;
	}

	frappe.db
		.get_value("Transport Location", selected_location, "area_zone")
		.then((response) => {
			if (frm.doc[location_field] !== selected_location) {
				return;
			}

			const area_zone = response && response.message ? response.message.area_zone || "" : "";
			frm.set_value(zone_field, area_zone);
			update_rule_name(frm);
		});
}

function update_rule_name(frm) {
	const loading = frm.doc.loading_location || frm.doc.loading_area_zone;
	const unloading = frm.doc.unloading_location || frm.doc.unloading_area_zone;
	const rule_name = loading && unloading ? `${loading} → ${unloading}` : "";

	if (frm.doc.rule_name !== rule_name) {
		frm.set_value("rule_name", rule_name);
	}
}
