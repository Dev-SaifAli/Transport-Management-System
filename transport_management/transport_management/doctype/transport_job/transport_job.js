frappe.ui.form.on("Transport Job", {
	refresh(frm) {
		frm.trigger("setup_location_queries");
		frm.trigger("add_trip_button");
	},

	setup_location_queries(frm) {
		frm.set_query("loading_site", () => ({
			filters: {
				active: 1,
				location_usage: ["in", ["Loading", "Both"]],
			},
		}));
		frm.set_query("unloading_site", () => ({
			filters: {
				active: 1,
				location_usage: ["in", ["Unloading", "Both"]],
			},
		}));
	},

	add_trip_button(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Create Transport Trip"), () => {
			frappe.call({
				method:
					"transport_management.transport_management.doctype.transport_trip.transport_trip.get_defaults_from_transport_job",
				args: {
					transport_job: frm.doc.name,
				},
				callback(r) {
					const defaults = r.message || {};
					frappe.new_doc("Transport Trip", defaults);
				},
			});
		});
	},
});
