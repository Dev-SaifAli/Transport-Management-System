frappe.pages["tms-toll-billing-review"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Toll / Extra Charges Billing Review"),
		single_column: true,
	});

	const state = { review: null };

	page.set_primary_action(__("Back to Transport Job"), () => {
		const job = get_transport_job();
		if (job) frappe.set_route("Form", "Transport Job", job);
	}, "arrow-left");

	$(page.body).html(`
		<div class="tms-toll-billing-review">
			<div class="frappe-card p-4" data-field="summary-card">
				<div class="text-muted">${__("Loading toll billing review...")}</div>
			</div>
			<div class="frappe-card p-4 mt-4">
				<div class="d-flex justify-content-between align-items-center mb-3">
					<h5 class="m-0">${__("Grouped Toll Commercial Preview")}</h5>
					<button class="btn btn-primary btn-sm" data-action="create-toll-invoice">
						${__("Create Toll Invoice")}
					</button>
				</div>
				<div class="table-responsive" data-field="grouping-preview"></div>
			</div>
			<div class="row mt-4">
				<div class="col-lg-8">
					<div class="frappe-card p-4">
						<h5 class="m-0">${__("Source Charge Rows")}</h5>
						<div class="table-responsive mt-3">
							<table class="table table-bordered table-sm">
								<thead>
									<tr>
										<th>${__("Trip No.")}</th>
										<th>${__("Trip Date")}</th>
										<th>${__("Loading Point")}</th>
										<th>${__("Unloading Point")}</th>
										<th>${__("Material")}</th>
										<th>${__("Charge Type")}</th>
										<th>${__("Rule")}</th>
										<th>${__("Rate Basis")}</th>
										<th class="text-right">${__("Quantity")}</th>
										<th class="text-right">${__("Rate")}</th>
										<th class="text-right">${__("Amount")}</th>
									</tr>
								</thead>
								<tbody data-field="charge-rows">
									<tr><td colspan="11" class="text-muted">${__("No charge rows loaded.")}</td></tr>
								</tbody>
							</table>
						</div>
					</div>
				</div>
				<div class="col-lg-4">
					<div class="frappe-card p-4">
						<h5 class="m-0">${__("Toll Summary")}</h5>
						<div class="row mt-3" data-field="toll-summary"></div>
					</div>
				</div>
			</div>
		</div>
	`);

	const $body = $(page.body);
	$body.find('[data-action="create-toll-invoice"]').on("click", () => create_toll_invoice());
	load_review();

	function get_transport_job() {
		const route_options = frappe.route_options || {};
		const query_job = new URLSearchParams(window.location.search).get("transport_job");
		return route_options.transport_job || query_job;
	}

	function load_review() {
		const transport_job = get_transport_job();
		if (!transport_job) {
			render_error(__("Open Toll Billing Review from a Ready for Toll Billing Transport Job."));
			return;
		}
		frappe.call({
			method: "transport_management.transport_management.doctype.transport_job.transport_job.get_toll_billing_review",
			args: { transport_job },
			freeze: true,
			freeze_message: __("Loading Toll Billing Review"),
			callback(r) {
				state.review = r.message || {};
				render_review();
			},
		});
	}

	function render_review() {
		render_summary();
		render_grouping_preview();
		render_charge_rows();
		render_totals();
		update_invoice_button();
	}

	function render_summary() {
		const summary = state.review.summary || {};
		const rows = [
			["Transport Job", summary.transport_job],
			["Customer", summary.customer],
			["Transport Sales Order", summary.transport_sales_order],
			["Customer LPO Number", summary.customer_lpo_number],
			["Job Status", summary.job_status],
			["Transport Billing Status", summary.billing_status],
			["Transport Sales Invoice", summary.transport_sales_invoice],
			["Toll Billing Status", summary.toll_billing_status],
			["Toll Sales Invoice", summary.toll_sales_invoice],
			["Closed Trips", summary.total_closed_trips],
			["Stored Toll Charges", format_currency(summary.total_toll_charges)],
		];
		$body.find('[data-field="summary-card"]').html(`
			<h5 class="m-0">${__("Transport Job Toll Billing")}</h5>
			<div class="row mt-3">
				${rows.map(([label, value]) => summary_item(label, value)).join("")}
			</div>
		`);
	}

	function render_grouping_preview() {
		const groups = state.review.groups || [];
		if (!groups.length) {
			$body.find('[data-field="grouping-preview"]').html(`<div class="text-muted">${__("No grouped toll charges found.")}</div>`);
			return;
		}
		$body.find('[data-field="grouping-preview"]').html(`
			<table class="table table-bordered table-sm mb-0">
				<thead>
					<tr>
						<th>${__("Description")}</th>
						<th>${__("Rate Basis")}</th>
						<th class="text-right">${__("QTY")}</th>
						<th class="text-right">${__("Unit Price / AED")}</th>
						<th class="text-right">${__("Taxable Amount")}</th>
						<th class="text-right">${__("VAT %")}</th>
						<th class="text-right">${__("VAT Amount")}</th>
						<th class="text-right">${__("AED / NET Amount")}</th>
					</tr>
				</thead>
				<tbody>
					${groups.map((row) => `
						<tr>
							<td>${escape_html(row.description || "")}</td>
							<td>${escape_html(row.rate_basis || "")}</td>
							<td class="text-right">${format_number(row.qty)}</td>
							<td class="text-right">${format_money(row.rate)}</td>
							<td class="text-right">${format_money(row.taxable_amount)}</td>
							<td class="text-right">${format_percent(row.vat_percent)}</td>
							<td class="text-right">${format_money(row.vat_amount)}</td>
							<td class="text-right">${format_money(row.net_amount)}</td>
						</tr>
					`).join("")}
				</tbody>
			</table>
		`);
	}

	function render_charge_rows() {
		const charges = state.review.charges || [];
		if (!charges.length) {
			$body.find('[data-field="charge-rows"]').html(
				`<tr><td colspan="11" class="text-muted">${__("No stored charge rows found.")}</td></tr>`
			);
			return;
		}
		$body.find('[data-field="charge-rows"]').html(charges.map((row) => `
			<tr>
				<td>${link_to("Transport Trip", row.trip)}</td>
				<td>${escape_html(row.trip_date || "")}</td>
				<td>${escape_html(row.loading_site || "")}</td>
				<td>${escape_html(row.unloading_site || "")}</td>
				<td>${escape_html(row.material || "")}</td>
				<td>${escape_html(row.charge_type || "")}</td>
				<td>${row.charge_rule ? link_to("Transport Charge Rule", row.charge_rule) : ""}</td>
				<td>${escape_html(row.rate_basis || "")}</td>
				<td class="text-right">${format_number(row.quantity)}</td>
				<td class="text-right">${format_money(row.rate)}</td>
				<td class="text-right">${format_money(row.amount)}</td>
			</tr>
		`).join(""));
	}

	function render_totals() {
		const totals = state.review.totals || {};
		render_metric_grid($body.find('[data-field="toll-summary"]'), [
			["Groups", totals.group_count],
			["Total Qty", format_number(totals.qty)],
			["Taxable Amount", format_currency(totals.taxable_amount)],
			["VAT Amount", format_currency(totals.vat_amount)],
			["Gross / Net Total", format_currency(totals.net_amount)],
		]);
	}

	function update_invoice_button() {
		const summary = state.review.summary || {};
		const group_count = (state.review.groups || []).length;
		const $button = $body.find('[data-action="create-toll-invoice"]');
		if (summary.toll_sales_invoice) {
			$button.removeClass("hide").prop("disabled", false).text(__("Open Toll Invoice"));
			return;
		}
		const can_create = summary.toll_billing_status === "Ready for Toll Billing" && group_count > 0;
		$button.toggleClass("hide", !can_create).prop("disabled", !can_create).text(__("Create Toll Invoice"));
	}

	function create_toll_invoice() {
		const transport_job = get_transport_job();
		const summary = state.review.summary || {};
		if (summary.toll_sales_invoice) {
			frappe.set_route("Form", "Sales Invoice", summary.toll_sales_invoice);
			return;
		}
		frappe.call({
			method: "transport_management.transport_management.doctype.transport_job.transport_job.create_toll_invoice",
			args: { transport_job },
			freeze: true,
			freeze_message: __("Creating Draft Toll Invoice"),
			callback(r) {
				const invoice = r.message && r.message.invoice;
				if (invoice) {
					frappe.msgprint({
						title: __("Toll Invoice Created"),
						indicator: "green",
						message: __('Draft Toll Invoice <a href="/app/sales-invoice/{0}">{0}</a> created successfully.', [
							frappe.utils.escape_html(invoice),
						]),
					});
				}
				load_review();
			},
		});
	}

	function render_error(message) {
		$body.find('[data-field="summary-card"]').html(`<div class="text-danger">${escape_html(message)}</div>`);
	}

	function render_metric_grid($target, rows) {
		$target.html(rows.map(([label, value]) => summary_item(label, value)).join(""));
	}

	function summary_item(label, value) {
		return `
			<div class="col-md-4 col-sm-6 col-6 mb-3">
				<div class="text-muted small">${__(label)}</div>
				<div class="font-weight-bold">${escape_html(value == null || value === "" ? "-" : value)}</div>
			</div>
		`;
	}

	function link_to(doctype, name) {
		if (!name) return "";
		const escaped = escape_html(name);
		const slug = doctype.toLowerCase().replace(/\s+/g, "-");
		return `<a href="/app/${slug}/${encodeURIComponent(name)}">${escaped}</a>`;
	}

	function format_currency(value) {
		return `AED ${format_money(value)}`;
	}

	function format_money(value) {
		return Number(value || 0).toLocaleString(undefined, {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		});
	}

	function format_number(value) {
		return Number(value || 0).toLocaleString(undefined, {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		});
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
		.tms-toll-billing-review .table { min-width: 1400px; }
	</style>`).appendTo("head");
};
