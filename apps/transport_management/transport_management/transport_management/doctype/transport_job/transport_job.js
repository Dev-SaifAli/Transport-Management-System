frappe.ui.form.on("Transport Job", {
	refresh(frm) {
		frm.trigger("setup_location_queries");
		frm.trigger("add_trip_button");
		frm.trigger("add_prepare_toll_billing_button");
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
		if (!can_create_transport_trip(frm)) {
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

	add_prepare_toll_billing_button(frm) {
		if (frm.is_new()) {
			return;
		}
		if (!can_use_transport_billing()) {
			return;
		}

		if (frm.doc.toll_sales_invoice) {
			frm.add_custom_button(__("Open Toll Invoice"), () => {
				frappe.set_route("Form", "Sales Invoice", frm.doc.toll_sales_invoice);
			}, __("Billing"));
			return;
		}

		if (frm.doc.toll_billing_status === "Ready for Toll Billing") {
			frm.add_custom_button(__("Prepare Toll Billing"), () => {
				frappe.call({
					method:
						"transport_management.transport_management.doctype.transport_job.transport_job.prepare_toll_billing",
					args: {
						transport_job: frm.doc.name,
					},
					callback(r) {
						const route = r.message && r.message.route;
						frappe.route_options = { transport_job: frm.doc.name };
						frappe.set_route(route || "tms-toll-billing-review");
					},
				});
			}, __("Billing"));
		}
	},
});

function can_create_transport_trip(frm) {
	return flt(frm.doc.remaining_quantity) > 0 && ["Draft", "Ready", "In Progress"].includes(frm.doc.status);
}

function can_use_transport_billing() {
	return ["Transport Manager", "Transport Admin", "System Manager"].some((role) => frappe.user.has_role(role));
}
