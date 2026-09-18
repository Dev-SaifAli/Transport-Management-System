frappe.pages["tms-billing-review"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Transport Sales Order Billing Review"),
		single_column: true,
	});

	const state = {
		review: null,
	};

	page.set_primary_action(__("Back to Sales Order"), () => {
		const sales_order = get_transport_sales_order();
		if (sales_order) {
			frappe.set_route("Form", "Transport Sales Order", sales_order);
		}
	}, "arrow-left");

	$(page.body).html(`
		<div class="tms-billing-review">
			<div class="frappe-card p-4" data-field="summary-card">
				<div class="text-muted">${__("Loading billing review...")}</div>
			</div>
			<div class="frappe-card p-4 mt-4 hide" data-field="invoice-summary-card"></div>
			<div class="frappe-card p-4 mt-4">
				<h5 class="m-0">${__("Linked Jobs")}</h5>
				<div class="table-responsive mt-3">
					<table class="table table-bordered table-sm">
						<thead>
							<tr>
								<th>${__("Transport Job")}</th>
								<th>${__("Sales Order Item")}</th>
								<th>${__("Material")}</th>
								<th>${__("Loading")}</th>
								<th>${__("Unloading")}</th>
								<th class="text-right">${__("Ordered Qty")}</th>
								<th class="text-right">${__("Delivered Qty")}</th>
								<th class="text-right">${__("Remaining Qty")}</th>
								<th>${__("Operational Status")}</th>
							</tr>
						</thead>
						<tbody data-field="job-rows">
							<tr><td colspan="9" class="text-muted">${__("No linked Jobs loaded.")}</td></tr>
						</tbody>
					</table>
				</div>
			</div>
			<div class="frappe-card p-4 mt-4">
				<div class="d-flex justify-content-between align-items-center mb-3">
					<h5 class="m-0">${__("Closed Source Trips")}</h5>
					<div class="d-flex align-items-center gap-2">
						<span class="text-muted small" data-field="trip-count"></span>
						<button class="btn btn-primary btn-sm" data-action="create-transport-invoice">
							${__("Create Transport Invoice")}
						</button>
					</div>
				</div>
				<div class="table-responsive">
					<table class="table table-bordered table-sm">
						<thead>
							<tr>
								<th>${__("Trip No.")}</th>
								<th>${__("Transport Job")}</th>
								<th>${__("Trip Date")}</th>
								<th>${__("GDN")}</th>
								<th>${__("Loading No.")}</th>
								<th>${__("Vehicle / Hired Vehicle")}</th>
								<th>${__("Driver / Hired Driver")}</th>
								<th>${__("Material")}</th>
								<th>${__("Route")}</th>
								<th class="text-right">${__("Delivered Quantity")}</th>
								<th class="text-right">${__("Unit Rate")}</th>
								<th class="text-right">${__("Taxable Amount")}</th>
								<th class="text-right">${__("VAT %")}</th>
								<th class="text-right">${__("VAT Amount")}</th>
								<th class="text-right">${__("Net Amount")}</th>
							</tr>
						</thead>
						<tbody data-field="trip-rows">
							<tr><td colspan="15" class="text-muted">${__("No billing review loaded.")}</td></tr>
						</tbody>
					</table>
				</div>
			</div>
			<div class="row mt-4">
				<div class="col-lg-8">
					<div class="frappe-card p-4">
						<h5 class="m-0">${__("Commercial Grouping Preview")}</h5>
						<div class="table-responsive mt-3" data-field="grouping-preview"></div>
					</div>
				</div>
				<div class="col-lg-4">
					<div class="frappe-card p-4">
						<h5 class="m-0">${__("Transport Summary")}</h5>
						<div class="row mt-3" data-field="transport-summary"></div>
					</div>
				</div>
			</div>
		</div>
	`);

	const $body = $(page.body);
	$body.find('[data-action="create-transport-invoice"]').on("click", () => create_transport_invoice());
	load_review();

	function get_transport_sales_order() {
		const route_options = frappe.route_options || {};
		const query_sales_order = new URLSearchParams(window.location.search).get("transport_sales_order");
		return route_options.transport_sales_order || query_sales_order;
	}

	function load_review() {
		const transport_sales_order = get_transport_sales_order();
		if (!transport_sales_order) {
			render_error(__("Open Billing Review from a Ready for Billing Transport Sales Order."));
			return;
		}

		frappe.call({
			method: "transport_management.transport_management.doctype.transport_job.transport_job.get_billing_review",
			args: { transport_sales_order },
			freeze: true,
			freeze_message: __("Loading Billing Review"),
			callback(r) {
				state.review = r.message || {};
				render_review();
			},
		});
	}

	function render_review() {
		render_summary();
		render_invoice_summary();
		render_job_rows();
		render_trip_rows();
		render_grouping_preview();
		render_totals();
		update_invoice_button();
	}

	function render_summary() {
		const summary = state.review.summary || {};
		const rows = [
			["Transport Sales Order", link_to("Transport Sales Order", summary.transport_sales_order)],
			["Customer", summary.customer],
			["Customer LPO Number", summary.customer_lpo_number],
			["Linked Jobs", summary.linked_jobs_count],
			["Closed Trips", summary.closed_trips_count],
			["Ordered Quantity", format_qty(summary.ordered_quantity)],
			["Delivered Quantity", format_qty(summary.delivered_quantity)],
			["Billing Status", summary.billing_status],
		];
		$body.find('[data-field="summary-card"]').html(`
			<h5 class="m-0">${__("Sales Order Summary")}</h5>
			<div class="row mt-3">
				${rows.map(([label, value]) => summary_item(label, value)).join("")}
			</div>
		`);
	}

	function render_invoice_summary() {
		const invoices = (state.review.summary && state.review.summary.existing_invoices) || [];
		const $card = $body.find('[data-field="invoice-summary-card"]');
		if (!invoices.length) {
			$card.addClass("hide").empty();
			return;
		}
		$card.removeClass("hide").html(`
			<h5 class="m-0">${__("Transport Billing")}</h5>
			<div class="table-responsive mt-3">
				<table class="table table-bordered table-sm mb-0">
					<thead>
						<tr>
							<th>${__("Invoice")}</th>
							<th>${__("Status")}</th>
							<th class="text-right">${__("Trips")}</th>
						</tr>
					</thead>
					<tbody>
						${invoices.map((row) => `
							<tr>
								<td>${link_to("Sales Invoice", row.invoice)}</td>
								<td>${escape_html(row.status || "")}</td>
								<td class="text-right">${cint(row.trips)}</td>
							</tr>
						`).join("")}
					</tbody>
				</table>
			</div>
		`);
	}

	function render_job_rows() {
		const jobs = state.review.jobs || [];
		if (!jobs.length) {
			$body.find('[data-field="job-rows"]').html(
				`<tr><td colspan="9" class="text-muted">${__("No linked Jobs found.")}</td></tr>`
			);
			return;
		}
		$body.find('[data-field="job-rows"]').html(jobs.map((row) => `
			<tr>
				<td>${link_to("Transport Job", row.transport_job)}</td>
				<td>${escape_html(row.sales_order_item || "")}</td>
				<td>${escape_html(row.material || "")}</td>
				<td>${escape_html(row.loading_site || "")}</td>
				<td>${escape_html(row.unloading_site || "")}</td>
				<td class="text-right">${format_qty(row.ordered_quantity)}</td>
				<td class="text-right">${format_qty(row.delivered_quantity)}</td>
				<td class="text-right">${format_qty(row.remaining_quantity)}</td>
				<td>${escape_html(row.status || "")}</td>
			</tr>
		`).join(""));
	}

	function render_trip_rows() {
		const trips = state.review.trips || [];
		$body.find('[data-field="trip-count"]').text(__("{0} invoice source trips", [trips.length]));
		if (!trips.length) {
			$body.find('[data-field="trip-rows"]').html(
				`<tr><td colspan="15" class="text-muted">${__("No closed billable trips found.")}</td></tr>`
			);
			return;
		}
		$body.find('[data-field="trip-rows"]').html(trips.map(render_trip_row).join(""));
	}

	function render_trip_row(row) {
		return `
			<tr>
				<td>${link_to("Transport Trip", row.trip)}</td>
				<td>${link_to("Transport Job", row.transport_job)}</td>
				<td>${escape_html(row.trip_date || "")}</td>
				<td>${escape_html(row.gdn || "")}</td>
				<td>${escape_html(row.loading_no || "")}</td>
				<td>${escape_html(row.vehicle || "")}</td>
				<td>${escape_html(row.driver || "")}</td>
				<td>${escape_html(row.material || "")}</td>
				<td><span class="tms-billing-route">${escape_html(row.route || "")}</span></td>
				<td class="text-right">${format_qty(row.delivered_quantity)}</td>
				<td class="text-right">${format_currency(row.unit_rate)}</td>
				<td class="text-right">${format_currency(row.taxable_amount)}</td>
				<td class="text-right">${format_percent(row.vat_percent)}</td>
				<td class="text-right">${format_currency(row.vat_amount)}</td>
				<td class="text-right">${format_currency(row.net_amount)}</td>
			</tr>
		`;
	}

	function render_grouping_preview() {
		const groups = state.review.groups || [];
		if (!groups.length) {
			$body.find('[data-field="grouping-preview"]').html(`<div class="text-muted">${__("No commercial groups found.")}</div>`);
			return;
		}
		$body.find('[data-field="grouping-preview"]').html(`
			<table class="table table-bordered table-sm">
				<thead>
					<tr>
						<th>${__("Description")}</th>
						<th>${__("Source Jobs")}</th>
						<th class="text-right">${__("Trips")}</th>
						<th class="text-right">${__("Qty")}</th>
						<th class="text-right">${__("Rate")}</th>
						<th class="text-right">${__("Taxable Amount")}</th>
						<th class="text-right">${__("VAT")}</th>
						<th class="text-right">${__("Net Amount")}</th>
					</tr>
				</thead>
				<tbody>
					${groups.map((row) => `
						<tr>
							<td>${escape_html(row.description || "")}</td>
							<td>${escape_html((row.job_names || []).join(", "))}</td>
							<td class="text-right">${cint(row.trip_count)}</td>
							<td class="text-right">${format_qty(row.qty)}</td>
							<td class="text-right">${format_currency(row.rate)}</td>
							<td class="text-right">${format_currency(row.taxable_amount)}</td>
							<td class="text-right">${format_currency(row.vat_amount)}</td>
							<td class="text-right">${format_currency(row.net_amount)}</td>
						</tr>
					`).join("")}
				</tbody>
			</table>
		`);
	}

	function render_totals() {
		const totals = state.review.totals || calculate_selected_totals(state.review.trips || []);
		render_metric_grid($body.find('[data-field="transport-summary"]'), [
			["Total Trips", totals.selected_trips],
			["Delivered Quantity", format_qty(totals.delivered_quantity)],
			["Taxable Amount", format_currency(totals.taxable_amount)],
			["VAT 5%", format_percent(5)],
			["VAT Amount", format_currency(totals.vat_amount)],
			["Gross / Net Total", format_currency(totals.net_amount)],
		]);
	}

	function update_invoice_button() {
		const summary = state.review && state.review.summary ? state.review.summary : {};
		const trip_count = (state.review && state.review.trips ? state.review.trips : []).length;
		const $button = $body.find('[data-action="create-transport-invoice"]');
		if (summary.transport_sales_invoice) {
			$button.removeClass("hide").prop("disabled", false).text(__("Open Transport Invoice"));
			return;
		}
		const can_create = summary.billing_status === "Ready for Billing" && trip_count > 0;
		$button.toggleClass("hide", !can_create).prop("disabled", !can_create).text(__("Create Transport Invoice"));
	}

	function create_transport_invoice() {
		const transport_sales_order = get_transport_sales_order();
		const summary = state.review.summary || {};
		if (summary.transport_sales_invoice) {
			frappe.set_route("Form", "Sales Invoice", summary.transport_sales_invoice);
			return;
		}
		frappe.call({
			method: "transport_management.transport_management.doctype.transport_job.transport_job.create_transport_invoice",
			args: { transport_sales_order },
			freeze: true,
			freeze_message: __("Creating Draft Transport Invoice"),
			callback(r) {
				const invoice = r.message && r.message.invoice;
				if (invoice) {
					frappe.msgprint({
						title: __("Transport Invoice Created"),
						indicator: "green",
						message: __(
							'Draft Transport Invoice <a href="/app/sales-invoice/{0}">{0}</a> created successfully.',
							[frappe.utils.escape_html(invoice)]
						),
					});
				}
				load_review();
			},
		});
	}

	function calculate_selected_totals(trips) {
		const selected = trips.filter((row) => row.selected);
		return {
			selected_trips: selected.length,
			delivered_quantity: sum(selected, "delivered_quantity", 6),
			taxable_amount: sum(selected, "taxable_amount", 2),
			vat_amount: sum(selected, "vat_amount", 2),
			net_amount: sum(selected, "net_amount", 2),
		};
	}

	function sum(rows, fieldname, precision) {
		return flt(rows.reduce((total, row) => total + flt(row[fieldname]), 0), precision);
	}

	function render_error(message) {
		$body.find('[data-field="summary-card"]').html(`<div class="text-danger">${escape_html(message)}</div>`);
	}

	function render_metric_grid($target, rows) {
		$target.html(rows.map(([label, value]) => summary_item(label, value)).join(""));
	}

	function summary_item(label, value) {
		const html = value == null || value === "" ? "-" : value;
		return `
			<div class="col-md-3 col-sm-4 col-6 mb-3">
				<div class="text-muted small">${__(label)}</div>
				<div class="font-weight-bold">${String(html).includes("<a ") ? html : escape_html(html)}</div>
			</div>
		`;
	}

	function link_to(doctype, name) {
		if (!name) return "";
		const escaped = escape_html(name);
		const slug = doctype.toLowerCase().replace(/\s+/g, "-");
		return `<a href="/app/${slug}/${encodeURIComponent(name)}">${escaped}</a>`;
	}

	function format_qty(value) {
		return `${Number(value || 0).toLocaleString(undefined, {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		})} TON`;
	}

	function format_currency(value) {
		return `AED ${Number(value || 0).toLocaleString(undefined, {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		})}`;
	}

	function format_percent(value) {
		return `${Number(value || 0).toLocaleString(undefined, {
			minimumFractionDigits: 0,
			maximumFractionDigits: 2,
		})}%`;
	}

	function escape_html(value) {
		return frappe.utils.escape_html(String(value == null ? "" : value));
	}

	$(`<style>
		.tms-billing-review .table { min-width: 1900px; }
		.tms-billing-route {
			display: inline-block;
			max-width: 240px;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
			vertical-align: bottom;
		}
	</style>`).appendTo("head");
};
