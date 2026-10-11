frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		apply_tms_transport_item_grid(frm);
	},

	tms_invoice_type(frm) {
		apply_tms_transport_item_grid(frm);
	},

	tms_get_transport_trips(frm) {
		show_transport_trip_selection(frm);
	},
});

function show_transport_trip_selection(frm) {
	if (!frm.doc.customer) {
		frappe.msgprint(__("Select a Customer first."));
		return;
	}
	if (!frm.doc.tms_billing_from_date || !frm.doc.tms_billing_to_date) {
		frappe.msgprint(__("Select From Date and To Date first."));
		return;
	}

	frappe.call({
		method: "transport_management.transport_management.doctype.transport_job.transport_job.get_customer_transport_invoice_trips",
		args: {
			customer: frm.doc.customer,
			from_date: frm.doc.tms_billing_from_date,
			to_date: frm.doc.tms_billing_to_date,
		},
		freeze: true,
		freeze_message: __("Loading eligible Transport Trips"),
		callback(r) {
			const trips = (r.message && r.message.trips) || [];
			if (!trips.length) {
				frappe.msgprint(__("No billable trips found for this customer and date range."));
				return;
			}
			open_transport_trip_dialog(frm, trips);
		},
	});
}

function open_transport_trip_dialog(frm, trips) {
	const dialog = new frappe.ui.Dialog({
		title: __("Select Transport Trips"),
		size: "extra-large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "trip_html",
			},
		],
		primary_action_label: __("Add to Sales Invoice"),
		primary_action() {
			const selected = [];
			dialog.$wrapper.find("[data-trip-check]:checked").each(function () {
				selected.push($(this).attr("data-trip-check"));
			});
			if (!selected.length) {
				frappe.msgprint(__("Select at least one Transport Trip."));
				return;
			}
			apply_transport_invoice_payload(frm, selected, dialog);
		},
	});

	dialog.fields_dict.trip_html.$wrapper.html(render_transport_trip_table(trips));
	dialog.show();
	dialog.$wrapper.find("[data-trip-toggle]").on("change", function () {
		dialog.$wrapper.find("[data-trip-check]").prop("checked", $(this).is(":checked"));
	});
}

function render_transport_trip_table(trips) {
	return `
		<div class="table-responsive" style="max-height: 460px; overflow: auto;">
			<table class="table table-bordered table-sm">
				<thead>
					<tr>
						<th style="width: 36px;"><input type="checkbox" data-trip-toggle checked></th>
						<th>${__("Trip No.")}</th>
						<th>${__("Transport Job")}</th>
						<th>${__("Loading Date")}</th>
						<th>${__("Delivery Date")}</th>
						<th>${__("Status")}</th>
						<th class="text-right">${__("Billable Quantity")}</th>
					</tr>
				</thead>
				<tbody>
					${trips.map(render_transport_trip_row).join("")}
				</tbody>
			</table>
		</div>
	`;
}

function render_transport_trip_row(row) {
	return `
		<tr>
			<td><input type="checkbox" data-trip-check="${escape_html(row.trip)}" checked></td>
			<td>${link_to("Transport Trip", row.trip)}</td>
			<td>${link_to("Transport Job", row.transport_job)}</td>
			<td>${escape_html(format_datetime(row.loading_datetime))}</td>
			<td>${escape_html(format_datetime(row.delivery_datetime))}</td>
			<td>${escape_html(row.status || "")}</td>
			<td class="text-right">${format_qty(row.delivered_quantity)}</td>
		</tr>
	`;
}

function apply_transport_invoice_payload(frm, selected_trips, dialog) {
	frappe.call({
		method: "transport_management.transport_management.doctype.transport_job.transport_job.get_transport_sales_invoice_payload",
		args: {
			customer: frm.doc.customer,
			company: frm.doc.company,
			from_date: frm.doc.tms_billing_from_date,
			to_date: frm.doc.tms_billing_to_date,
			trip_names: selected_trips,
		},
		freeze: true,
		freeze_message: __("Preparing Sales Invoice items"),
		callback(r) {
			const payload = r.message || {};
			apply_transport_payload_to_invoice(frm, payload);
			dialog.hide();
			frappe.show_alert({
				message: __("{0} Transport Trips added to Sales Invoice.", [selected_trips.length]),
				indicator: "green",
			});
		},
	});
}

function apply_transport_payload_to_invoice(frm, payload) {
	const header = payload.header || {};
	for (const [fieldname, value] of Object.entries(header)) {
		frm.set_value(fieldname, value);
	}

	frm.clear_table("items");
	for (const row of payload.items || []) {
		Object.assign(frm.add_child("items"), row);
	}

	frm.clear_table("taxes");
	for (const row of payload.taxes || []) {
		Object.assign(frm.add_child("taxes"), row);
	}

	if (frm.fields_dict.tms_source_jobs) {
		frm.clear_table("tms_source_jobs");
		for (const row of payload.source_jobs || []) {
			Object.assign(frm.add_child("tms_source_jobs"), row);
		}
	}

	frm.refresh_fields(["items", "taxes", "tms_source_jobs"]);
	apply_tms_transport_item_grid(frm);
}

function apply_tms_transport_item_grid(frm) {
	const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
	if (!grid) return;

	const is_transport_invoice = frm.doc.tms_invoice_type === "Transport";
	const is_toll_invoice = frm.doc.tms_invoice_type === "Toll / Extra Charges";
	for (const fieldname of ["tms_loading_location", "tms_unloading_location", "tms_material"]) {
		grid.update_docfield_property(fieldname, "in_list_view", is_transport_invoice ? 1 : 0);
	}
	for (const fieldname of ["tms_charge_type", "tms_rate_basis", "tms_charge_rule"]) {
		grid.update_docfield_property(fieldname, "in_list_view", is_toll_invoice ? 1 : 0);
	}
	grid.update_docfield_property("warehouse", "hidden", is_transport_invoice || is_toll_invoice ? 1 : 0);
	frm.refresh_field("items");
}

function link_to(doctype, name) {
	if (!name) return "";
	const label = escape_html(name);
	const slug = doctype.toLowerCase().replace(/\s+/g, "-");
	return `<a href="/app/${slug}/${encodeURIComponent(name)}">${label}</a>`;
}

function format_datetime(value) {
	return value ? frappe.datetime.str_to_user(value) : "";
}

function format_qty(value) {
	return format_number(value || 0, null, 6);
}

function escape_html(value) {
	return frappe.utils.escape_html(String(value == null ? "" : value));
}
