frappe.ui.form.on("Transport Trip", {
	refresh(frm) {
		frm.set_df_property("status", "read_only", 1);
		frm.set_df_property("status", "hidden", 1);
		frm.trigger("setup_transporter_query");
		frm.trigger("setup_location_queries");
		frm.trigger("setup_vehicle_query");
		frm.trigger("setup_hired_vehicle_query");
		frm.trigger("toggle_execution_fields");
		frm.trigger("toggle_pod_fields");
		frm.trigger("toggle_charge_fields");
		frm.trigger("render_status_header");
		frm.trigger("setup_status_actions");
		frm.trigger("add_calculate_charges_button");
	},

	execution_source(frm) {
		frm.trigger("toggle_execution_fields");
		frm.trigger("setup_vehicle_query");
		frm.trigger("setup_hired_vehicle_query");
	},

	transport_job(frm) {
		frm.trigger("set_defaults_from_transport_job");
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
		frm.trigger("render_status_header");
		frm.trigger("setup_status_actions");
	},

	toll_applicable(frm) {
		frm.trigger("toggle_charge_fields");
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
		frm.toggle_display("transporter", is_hired);
		frm.toggle_display("hired_vehicle", is_hired);
		frm.toggle_display("hired_driver", is_hired);
		frm.toggle_display("vehicle", !is_hired);
		frm.toggle_display("driver", !is_hired);
		frm.set_df_property("transporter", "reqd", is_hired);
		frm.set_df_property("hired_vehicle", "reqd", is_hired);
		frm.set_df_property("vehicle", "reqd", !is_hired);
		frm.set_df_property("driver", "reqd", !is_hired);
	},

	toggle_pod_fields(frm) {
		frm.set_df_property("pod_attachment", "reqd", frm.doc.status === "POD_RECEIVED");
	},

	toggle_charge_fields(frm) {
		const show_tolls = Boolean(frm.doc.toll_applicable);
		frm.toggle_display("rak_toll", show_tolls);
		frm.toggle_display("sharjah_toll", show_tolls);
	},

	render_status_header(frm) {
		const steps = [
			["PLANNED", __("Planned")],
			["ASSIGNED", __("Assigned")],
			["LOADED", __("Loaded")],
			["IN_TRANSIT", __("In Transit")],
			["DELIVERED", __("Delivered")],
			["POD_RECEIVED", __("POD Received")],
			["CLOSED", __("Closed")],
		];
		const current = frm.doc.status || "PLANNED";
		const current_index = steps.findIndex(([status]) => status === current);
		const help = {
			PLANNED: __("Select execution details, then assign the trip."),
			ASSIGNED: __("Enter Loaded Quantity and Loading Date/Time, then mark the trip as Loaded."),
			LOADED: __("Start the journey once the loaded trip is ready to depart."),
			IN_TRANSIT: __("After delivery, enter Delivered Quantity and Delivery Date/Time."),
			DELIVERED: __("Confirm POD when the delivery proof is received."),
			POD_RECEIVED: __("Close the trip after final operational checks."),
			CLOSED: __("Trip is closed."),
			CANCELLED: __("Trip is cancelled."),
			EXCEPTION: __("Trip is marked as an exception."),
		};
		const step_html = steps
			.map(([status, label], index) => {
				let state = "future";
				if (status === current) {
					state = "current";
				} else if (current_index > -1 && index < current_index) {
					state = "complete";
				}
				const arrow = index < steps.length - 1 ? '<span class="tms-trip-arrow">&rarr;</span>' : "";
				return `<span class="tms-trip-step ${state}">${frappe.utils.escape_html(label)}</span>${arrow}`;
			})
			.join("");
		const header_html = `
			<div class="tms-trip-workflow-header">
				<div class="tms-trip-steps">${step_html}</div>
				<div class="tms-trip-help">${frappe.utils.escape_html(help[current] || "")}</div>
			</div>
			<style>
				.tms-trip-workflow-header {
					background: var(--card-bg);
					border: 1px solid var(--border-color);
					border-radius: 8px;
					margin: 0 0 12px;
					padding: 12px 14px;
				}
				.tms-trip-steps { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
				.tms-trip-step {
					border: 1px solid var(--border-color);
					border-radius: 999px;
					color: var(--text-muted);
					font-size: 12px;
					line-height: 1;
					padding: 5px 9px;
					white-space: nowrap;
				}
				.tms-trip-step.complete {
					background: var(--green-50);
					border-color: var(--green-200);
					color: var(--green-700);
				}
				.tms-trip-step.current {
					background: var(--blue-50);
					border-color: var(--blue-300);
					color: var(--blue-700);
					font-weight: 600;
				}
				.tms-trip-arrow { color: var(--text-muted); font-size: 12px; }
				.tms-trip-help { color: var(--text-muted); font-size: 12px; margin-top: 8px; }
				.tms-trip-main-action {
					border: 0;
					color: #fff;
					font-weight: 600;
				}
				.tms-trip-main-action.tms-blue { background: #1f6feb; }
				.tms-trip-main-action.tms-amber { background: #b7791f; }
				.tms-trip-main-action.tms-indigo { background: #4f46e5; }
				.tms-trip-main-action.tms-green { background: #238636; }
				.tms-trip-main-action.tms-purple { background: #7e22ce; }
				.tms-trip-main-action.tms-dark { background: #374151; }
				.tms-trip-main-action:hover,
				.tms-trip-main-action:focus { color: #fff; filter: brightness(0.95); }
			</style>
		`;
		let $header = frm.$wrapper.find(".tms-trip-workflow-header-container");
		if (!$header.length) {
			$header = $('<div class="tms-trip-workflow-header-container"></div>');
			const $target = frm.$wrapper.find(".form-layout").first();
			if ($target.length) {
				$header.insertBefore($target);
			} else {
				frm.$wrapper.prepend($header);
			}
		}
		$header.html(header_html);
	},

	setup_status_actions(frm) {
		frm.clear_custom_buttons();
		if (frm.is_new()) return;

		const next_action = get_next_trip_action(frm.doc.status);
		if (next_action) {
			let $button;
			$button = frm.add_custom_button(next_action.label, () => {
				frm.events.transition_status(frm, next_action.status, $button);
			});
			if ($button) {
				$button
					.removeClass("btn-default")
					.addClass(`btn-primary tms-trip-main-action ${next_action.color}`);
			}
		}

		if (["PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT"].includes(frm.doc.status)) {
			let $cancel_button;
			$cancel_button = frm.add_custom_button(__("Cancel Trip"), () => {
				frm.events.transition_status(frm, "CANCELLED", $cancel_button);
			}, __("Actions"));
		}
		if (["ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED"].includes(frm.doc.status)) {
			let $exception_button;
			$exception_button = frm.add_custom_button(__("Report Exception"), () => {
				frm.events.transition_status(frm, "EXCEPTION", $exception_button);
			}, __("Actions"));
		}
	},

	add_calculate_charges_button(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Calculate Charges"), () => {
			const run_calculation = () =>
				frappe.call({
					method:
						"transport_management.transport_management.doctype.transport_trip.transport_trip.calculate_charges",
					args: {
						transport_trip: frm.doc.name,
					},
					freeze: true,
					freeze_message: __("Calculating Transport Charges"),
				});

			const save_current_changes = frm.is_dirty() ? frm.save() : Promise.resolve();
			save_current_changes
				.then(run_calculation)
				.then((r) => {
					const totals = (r.message && r.message.totals) || {};
					frappe.show_alert({
						message: __("Transport charges calculated. Total: AED {0}", [
							Number(totals.total_extra_charges || 0).toLocaleString(undefined, {
								minimumFractionDigits: 2,
								maximumFractionDigits: 2,
							}),
						]),
						indicator: "green",
					});
					return frm.reload_doc();
				});
		}, __("Actions"));
	},

	transition_status(frm, target_status, $button) {
		const current_status = frm.doc.status || "PLANNED";
		const next_action = get_next_trip_action(current_status);
		const status = target_status || (next_action && next_action.status);
		if (!status) return Promise.resolve();

		const set_button_state = (disabled) => {
			if (!$button || !$button.length) return;
			$button.prop("disabled", disabled).toggleClass("disabled", disabled);
		};
		const reload_from_server = () => frm.reload_doc();
		const call_transition = () =>
			frappe.call({
				method:
					"transport_management.transport_management.doctype.transport_trip.transport_trip.transition_trip_status",
				args: {
					transport_trip: frm.doc.name,
					status,
				},
				freeze: true,
				freeze_message: __("Updating Transport Trip status"),
			});

		set_button_state(true);
		const save_current_changes = frm.is_dirty() ? frm.save() : Promise.resolve();
		return save_current_changes
			.then(call_transition)
			.then(reload_from_server)
			.catch((error) => {
				return reload_from_server().then(() => {
					throw error;
				});
			})
			.finally(() => {
				set_button_state(false);
			});
	},

	set_defaults_from_transport_job(frm) {
		if (!frm.doc.transport_job) return;
		frappe.call({
			method:
				"transport_management.transport_management.doctype.transport_trip.transport_trip.get_defaults_from_transport_job",
			args: {
				transport_job: frm.doc.transport_job,
			},
			callback(r) {
				const defaults = r.message || {};
				["trip_date", "loading_site", "unloading_site", "material", "uom"].forEach((fieldname) => {
					if (defaults[fieldname]) {
						frm.set_value(fieldname, defaults[fieldname]);
					}
				});
			},
		});
	},
});

function get_next_trip_action(status) {
	const actions = {
		PLANNED: { status: "ASSIGNED", action: "assign", label: __("Assign Trip"), color: "tms-blue" },
		ASSIGNED: { status: "LOADED", action: "mark_loaded", label: __("Mark as Loaded"), color: "tms-amber" },
		LOADED: { status: "IN_TRANSIT", action: "start_journey", label: __("Start Journey"), color: "tms-indigo" },
		IN_TRANSIT: { status: "DELIVERED", action: "mark_delivered", label: __("Mark Delivered"), color: "tms-green" },
		DELIVERED: { status: "POD_RECEIVED", action: "confirm_pod", label: __("Confirm POD"), color: "tms-purple" },
		POD_RECEIVED: { status: "CLOSED", action: "close", label: __("Close Trip"), color: "tms-dark" },
	};
	return actions[status] || null;
}
