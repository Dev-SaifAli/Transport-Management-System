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
		frm.trigger("setup_vehicle_query");
		frm.trigger("setup_hired_vehicle_query");
	},

	transport_job(frm) {
		frm.trigger("setup_vehicle_query");
		frm.trigger("setup_hired_vehicle_query");
		frm.trigger("clear_incompatible_hired_vehicle");
	},

	material(frm) {
		frm.trigger("setup_vehicle_query");
		frm.trigger("setup_hired_vehicle_query");
		frm.trigger("clear_incompatible_vehicle");
		frm.trigger("clear_incompatible_hired_vehicle");
	},

	transporter(frm) {
		frm.trigger("setup_hired_vehicle_query");
		frm.trigger("clear_hired_vehicle_for_changed_transporter");
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
			query: "transport_management.cargo_type_master.compatible_hired_vehicle_query",
			filters: {
				transporter: frm.doc.transporter || "",
				material: frm.doc.material || "",
				transport_job: frm.doc.transport_job || "",
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
			query: "transport_management.cargo_type_master.compatible_owned_truck_query",
			filters: {
				material: frm.doc.material || "",
			},
		}));
	},

	clear_incompatible_vehicle(frm) {
		if (!frm.doc.vehicle || frm.doc.execution_source === "HIRED") return;
		frappe.call({
			method: "transport_management.cargo_type_master.get_compatible_owned_trucks",
			args: { material: frm.doc.material },
			callback(r) {
				const compatible = r.message || [];
				if (!compatible.includes(frm.doc.vehicle)) {
					frm.set_value("vehicle", null);
				}
			},
		});
	},

	clear_hired_vehicle_for_changed_transporter(frm) {
		if (!frm.doc.hired_vehicle || frm.doc.execution_source !== "HIRED") return;
		frappe.db.get_value("Hired Vehicle", frm.doc.hired_vehicle, "transporter").then((r) => {
			const vehicle_transporter = r.message && r.message.transporter;
			if (vehicle_transporter && vehicle_transporter !== frm.doc.transporter) {
				frm.set_value("hired_vehicle", null);
			}
		});
	},

	clear_incompatible_hired_vehicle(frm) {
		if (!frm.doc.hired_vehicle || frm.doc.execution_source !== "HIRED") return;
		frappe.call({
			method: "transport_management.cargo_type_master.get_compatible_hired_vehicles",
			args: {
				material: frm.doc.material,
				transport_job: frm.doc.transport_job,
				transporter: frm.doc.transporter,
			},
			callback(r) {
				const compatible = r.message || [];
				if (!compatible.includes(frm.doc.hired_vehicle)) {
					frm.set_value("hired_vehicle", null);
					frappe.show_alert({
						message: __("Selected Hired Vehicle is not compatible with the current material and transporter."),
						indicator: "orange",
					});
				}
			},
		});
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
