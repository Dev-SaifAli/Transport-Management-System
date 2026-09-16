frappe.ui.form.on("Transport Rate", {
	refresh(frm) {
		frm.set_query("loading_location", () => ({
			filters: {
				active: 1,
				location_usage: ["in", ["Loading", "Both"]]
			}
		}));
		frm.set_query("unloading_location", () => ({
			filters: {
				active: 1,
				location_usage: ["in", ["Unloading", "Both"]]
			}
		}));
	}
});
