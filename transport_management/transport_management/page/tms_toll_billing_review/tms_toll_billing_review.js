frappe.pages["tms-toll-billing-review"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Toll / Extra Charges Billing Review"),
		single_column: true,
	});

	const state = { review: null, invoice_preview: null };

	page.set_primary_action(__("Back to Transport Job"), () => {
		const job = get_transport_job();
		if (job) frappe.set_route("Form", "Transport Job", job);
	}, "arrow-left");

	$(page.body).html(`
		<div class="tms-toll-billing-review">
			<div class="frappe-card p-4" data-field="summary-card">
				<div class="text-muted">${__("Loading toll billing review...")}</div>
			</div>
			<div class="mt-4" data-field="invoice-preview"></div>
			<div class="frappe-card p-4 mt-4" data-field="grouping-card">
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
	$body.on("click", '[data-action="print-toll-invoice"]', () => print_invoice_preview());
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
				state.invoice_preview = null;
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
		load_invoice_preview();
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

	function load_invoice_preview() {
		const summary = state.review.summary || {};
		const invoice = summary.toll_sales_invoice;
		if (!invoice) {
			$body.find('[data-field="invoice-preview"]').empty();
			$body.find('[data-field="grouping-card"]').removeClass("hide");
			return;
		}

		$body.find('[data-field="grouping-card"]').addClass("hide");
		$body.find('[data-field="invoice-preview"]').html(
			`<div class="text-muted">${__("Loading Toll Invoice preview...")}</div>`
		);
		frappe.call({
			method: "transport_management.transport_management.doctype.transport_job.transport_job.get_toll_invoice_preview",
			args: { invoice, transport_job: summary.transport_job },
			callback(r) {
				state.invoice_preview = r.message || null;
				render_invoice_preview();
			},
		});
	}

	function render_invoice_preview() {
		const invoice = state.invoice_preview;
		if (!invoice) {
			$body.find('[data-field="invoice-preview"]').empty();
			return;
		}

		$body.find('[data-field="invoice-preview"]').html(`
			<div class="tms-toll-invoice-toolbar">
				<div>
					<span class="text-muted">${__("Sales Invoice")}:</span>
					${link_to("Sales Invoice", invoice.name)}
					<span class="badge badge-secondary ml-2">${escape_html(invoice.status || "")}</span>
				</div>
				<button class="btn btn-sm btn-primary" data-action="print-toll-invoice">${__("Print Invoice")}</button>
			</div>
			${render_invoice_document(invoice)}
		`);
	}

	function render_invoice_document(invoice) {
		const rows = invoice.items || [];
		const taxes = invoice.taxes || [];
		return `
			<section class="tms-tax-invoice-preview" data-field="printable-toll-invoice">
				<table class="tms-tax-invoice-header">
					<tr>
						<td class="party-cell">
							<div class="party-title">${escape_html(invoice.company || "AL RANA TRANSPORT LLC")}</div>
							${header_line("Invoice No", invoice.name)}
							${header_line("Date", format_date(invoice.posting_date))}
							${header_line("PO No", invoice.po_no || invoice.customer_lpo_number)}
							${header_line("PO Box", extract_po_box(invoice.company_address))}
							${header_line("Phone", invoice.company_phone)}
							${header_line("TRN", invoice.company_tax_id)}
						</td>
						<td class="title-cell">
							<div class="invoice-title">${__("TAX INVOICE")}</div>
						</td>
						<td class="party-cell">
							<div class="party-title">${escape_html(invoice.customer_name || invoice.customer || "")}</div>
							${header_line("Address", multiline(invoice.customer_address), true)}
							${header_line("PO Box", extract_po_box(invoice.customer_address))}
							${header_line("Phone", invoice.customer_phone)}
							${header_line("TRN", invoice.customer_tax_id)}
						</td>
					</tr>
				</table>

				<table class="tms-tax-invoice-items">
					<thead>
						<tr>
							<th>${__("Sr.No")}</th>
							<th>${__("Description")}</th>
							<th>${__("Qty")}</th>
							<th>${__("Unit Price / AED")}</th>
							<th>${__("Taxable Amount")}</th>
							<th>${__("VAT Rate")}</th>
							<th>${__("VAT Amount")}</th>
							<th>${__("AED / Net Amount")}</th>
						</tr>
					</thead>
					<tbody>
						${rows.map((row) => `
							<tr>
								<td class="text-center">${escape_html(row.idx)}</td>
								<td>${escape_html(row.description || "")}</td>
								<td class="text-right">${format_number(row.qty)}</td>
								<td class="text-right">${format_money(row.rate)}</td>
								<td class="text-right">${format_money(row.taxable_amount)}</td>
								<td class="text-right">${format_percent(row.vat_rate)}</td>
								<td class="text-right">${format_money(row.vat_amount)}</td>
								<td class="text-right">${format_money(row.net_amount)}</td>
							</tr>
						`).join("")}
					</tbody>
					<tfoot>
						<tr>
							<td colspan="4" class="text-right">${__("Net Total")}</td>
							<td class="text-right">${format_money(invoice.net_total)}</td>
							<td></td>
							<td class="text-right">${format_money(invoice.total_taxes_and_charges)}</td>
							<td class="text-right">${format_money(invoice.grand_total)}</td>
						</tr>
					</tfoot>
				</table>

				<div class="tms-tax-invoice-bottom">
					<div class="amount-words">
						<strong>${__("Amount in Words")}:</strong>
						${escape_html(invoice.in_words || "")}
						${render_tax_accounts(taxes)}
					</div>
					<table class="tms-tax-invoice-totals">
						<tr><td>${__("Net Total")}</td><td>${format_money(invoice.net_total)}</td></tr>
						<tr><td>${__("Total VAT")}</td><td>${format_money(invoice.total_taxes_and_charges)}</td></tr>
						<tr><td>${__("Grand Total")}</td><td>${format_money(invoice.grand_total)}</td></tr>
						<tr><td>${__("Outstanding Amount")}</td><td>${format_money(invoice.outstanding_amount)}</td></tr>
					</table>
				</div>
			</section>
		`;
	}

	function render_tax_accounts(taxes) {
		if (!taxes || !taxes.length) return "";
		return `
			<div class="tax-account-note">
				<strong>${__("Tax Rows")}:</strong>
				${taxes.map((tax) => `${escape_html(tax.account_head || tax.description || "")} (${format_percent(tax.rate)}: ${format_money(tax.tax_amount)})`).join(", ")}
			</div>
		`;
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

	function print_invoice_preview() {
		const printable = $body.find('[data-field="printable-toll-invoice"]').get(0);
		if (!printable) return;
		const print_window = window.open("", "_blank");
		if (!print_window) {
			frappe.msgprint(__("Please allow popups to print the invoice preview."));
			return;
		}
		print_window.document.write(`
			<!doctype html>
			<html>
				<head>
					<title>${__("Toll Invoice")}</title>
					<style>${get_invoice_print_css()}</style>
				</head>
				<body>${printable.outerHTML}</body>
			</html>
		`);
		print_window.document.close();
		print_window.focus();
		print_window.print();
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

	function header_line(label, value, value_is_html) {
		const display_value = value ? (value_is_html ? value : escape_html(value)) : "-";
		return `
			<div class="header-line">
				<span>${__(label)}:</span>
				<strong>${display_value}</strong>
			</div>
		`;
	}

	function multiline(value) {
		return escape_html(value || "").replace(/\n/g, "<br>");
	}

	function extract_po_box(address) {
		const value = String(address || "");
		const match = value.match(/P\\.?\\s*O\\.?\\s*Box[^<\\n,]*/i);
		return match ? escape_html(match[0]) : "";
	}

	function format_date(value) {
		return value ? frappe.datetime.str_to_user(value) : "";
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

	function get_invoice_print_css() {
		return `
			@page { size: A4 portrait; margin: 10mm; }
			body { background: #fff; color: #111; font-family: Arial, Helvetica, sans-serif; font-size: 10.5px; }
			.tms-tax-invoice-preview { background: #fff; color: #111; margin: 0 auto; max-width: 210mm; }
			.tms-tax-invoice-header,
			.tms-tax-invoice-items,
			.tms-tax-invoice-totals { border-collapse: collapse; width: 100%; }
			.tms-tax-invoice-header td,
			.tms-tax-invoice-items th,
			.tms-tax-invoice-items td,
			.tms-tax-invoice-totals td { border: 1px solid #222; padding: 4px 5px; vertical-align: top; }
			.tms-tax-invoice-header { margin-bottom: 8px; }
			.tms-tax-invoice-header .party-cell { width: 38%; }
			.tms-tax-invoice-header .title-cell { text-align: center; vertical-align: top; width: 24%; }
			.tms-tax-invoice-preview .party-title { font-size: 12px; font-weight: 700; margin-bottom: 5px; text-transform: uppercase; }
			.tms-tax-invoice-preview .invoice-title { font-size: 15px; font-weight: 700; margin-top: 2px; text-transform: uppercase; }
			.tms-tax-invoice-preview .header-line { display: flex; gap: 5px; line-height: 1.35; }
			.tms-tax-invoice-preview .header-line span { min-width: 58px; }
			.tms-tax-invoice-preview .header-line strong { font-weight: 600; }
			.tms-tax-invoice-items th { background: #f3f3f3; font-weight: 700; text-align: center; }
			.tms-tax-invoice-items tfoot td { font-weight: 700; }
			.tms-tax-invoice-preview .text-right { text-align: right; }
			.tms-tax-invoice-preview .text-center { text-align: center; }
			.tms-tax-invoice-bottom { display: grid; gap: 10px; grid-template-columns: 1fr 220px; margin-top: 8px; }
			.tms-tax-invoice-preview .amount-words { border: 1px solid #222; min-height: 72px; padding: 6px; }
			.tms-tax-invoice-preview .tax-account-note { margin-top: 8px; }
			.tms-tax-invoice-totals td:first-child { font-weight: 700; }
			.tms-tax-invoice-totals td:last-child { text-align: right; }
		`;
	}

	$(`<style>
		.tms-toll-billing-review .table { min-width: 1400px; }
		.tms-toll-invoice-toolbar {
			align-items: center;
			display: flex;
			justify-content: space-between;
			margin-bottom: 12px;
		}
		.tms-tax-invoice-preview {
			background: #fff;
			border: 1px solid #d8d8d8;
			box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
			color: #111;
			font-family: Arial, Helvetica, sans-serif;
			font-size: 10.5px;
			margin: 0 auto;
			max-width: 210mm;
			padding: 10mm;
		}
		${get_invoice_print_css()}
		@media print {
			body * { visibility: hidden; }
			[data-field="printable-toll-invoice"], [data-field="printable-toll-invoice"] * { visibility: visible; }
			[data-field="printable-toll-invoice"] { left: 0; position: absolute; top: 0; width: 100%; }
		}
	</style>`).appendTo("head");
};
