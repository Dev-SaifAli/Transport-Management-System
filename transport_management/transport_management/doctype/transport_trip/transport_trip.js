frappe.ui.form.on("Transport Trip", {
	refresh(frm) {
		frm.trigger("setup_transporter_query");
		frm.trigger("setup_location_queries");
		frm.trigger("setup_vehicle_query");
		frm.trigger("setup_hired_vehicle_query");
		frm.trigger("toggle_execution_fields");
		frm.trigger("toggle_pod_fields");
	},

	execution_source(frm) {
		frm.trigger("toggle_execution_fields");
	},

	transporter(frm) {
		frm.set_value("hired_vehicle", null);
	},

	status(frm) {
		frm.trigger("toggle_pod_fields");
	},

	setup_transporter_query(frm) {
		frm.set_query("transporter", () => ({
			filters: {
				is_transporter: 1,
				transporter_status: "Active",
				disabled: 0,
			},
		}));
	},

	setup_hired_vehicle_query(frm) {
		frm.set_query("hired_vehicle", () => ({
			filters: {
				transporter: frm.doc.transporter || "",
				active: 1,
			},
		}));
	},

	setup_location_queries(frm) {
		["loading_site", "unloading_site"].forEach((fieldname) => {
			frm.set_query(fieldname, () => ({
				filters: { active: 1 },
			}));
		});
	},

	setup_vehicle_query(frm) {
		frm.set_query("vehicle", () => ({
			filters: {
				disabled: 0,
				status: "Idle",
			},
		}));
	},

	toggle_execution_fields(frm) {
		const is_hired = frm.doc.execution_source === "HIRED";
		frm.set_df_property("transporter", "reqd", is_hired);
		frm.set_df_property("hired_vehicle", "reqd", is_hired);
		frm.set_df_property("vehicle", "reqd", !is_hired);
		frm.set_df_property("driver", "reqd", !is_hired);
	},

	toggle_pod_fields(frm) {
		frm.set_df_property("pod_attachment", "reqd", frm.doc.status === "POD_RECEIVED");
	},
});
