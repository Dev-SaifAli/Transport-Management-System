// Reports section of the AL RANA Dispatch console.

frappe.provide("dispatch_portal.views");

dispatch_portal.views.reports = {
	render(context) {
		this.container = context.container;
		this.console = context.console;
		this.permissions = context.permissions || {};
		this.charts = [];

		context.console.set_actions([
			{label: __("Refresh"), icon: "rotate-cw", onClick: () => this.load()},
			{
				label: __("Export CSV"),
				icon: "download",
				primary: true,
				onClick: () => this.export_csv(),
			},
		]);

		this.render_filters();
		this.load();
	},

	render_filters() {
		const utils = dispatch_portal.utils;
		const today = new Date();
		const thirty_days_ago = new Date();
		thirty_days_ago.setDate(today.getDate() - 30);

		const to = today.toISOString().slice(0, 10);
		const from = thirty_days_ago.toISOString().slice(0, 10);

		this.container.html(`
			<form class="al-dispatch-filters" data-report-filters>
				<div class="al-dispatch-field">
					<label>${__("From date")}</label>
					<input type="date" name="from_date" value="${from}" />
				</div>
				<div class="al-dispatch-field">
					<label>${__("To date")}</label>
					<input type="date" name="to_date" value="${to}" />
				</div>
				<div class="al-dispatch-filters-actions">
					<button type="button" class="btn btn-sm btn-primary" data-report-apply>
						${frappe.utils.icon("funnel")}<span>${__("Apply")}</span>
					</button>
				</div>
			</form>
			<div data-report-body></div>
		`);

		this.$body = this.container.find("[data-report-body]");
		this.container.find("[data-report-apply]").on("click", () => this.load());
		this.container.find("[data-report-filters]").on("submit", (event) => {
			event.preventDefault();
			this.load();
		});
	},

	range() {
		const values = {};
		this.container.find("[data-report-filters]").serializeArray().forEach((row) => {
			values[row.name] = row.value;
		});
		return values;
	},

	load() {
		const me = this;
		const range = this.range();
		this.$body.html(
			`<div class="al-dispatch-loading"><span class="al-dispatch-spinner"></span><span>${__(
				"Loading reports"
			)}</span></div>`
		);

		this.charts.forEach((chart) => chart.destroy && chart.destroy());
		this.charts = [];

		this.console
			.call({
				method: "dispatch_portal.api.reports.get_reports",
				args: {from_date: range.from_date, to_date: range.to_date},
			})
			.then((response) => me.render_body(response.message || {}))
			.catch((error) => {
				me.$body.html(
					`<div class="al-dispatch-error">${dispatch_portal.utils.server_message(error)}</div>`
				);
			});
	},

	render_body(data) {
		const utils = dispatch_portal.utils;
		this.$body.html(`
			<div class="al-dispatch-grid al-dispatch-grid-4" style="margin-bottom:16px">
				${this.total_card(__("Trips"), data.trips_by_status)}
				${this.quantity_card(__("Planned Quantity"), data.quantity_delivered.planned)}
				${this.quantity_card(__("Loaded Quantity"), data.quantity_delivered.loaded)}
				${this.quantity_card(__("Delivered Quantity"), data.quantity_delivered.delivered)}
			</div>
			<div class="al-dispatch-grid al-dispatch-grid-2">
				${utils.panel(
					__("Trips by Status"),
					"",
					`<div class="al-dispatch-chart" data-chart="status"></div>`
				)}
				${utils.panel(
					__("Trips by Customer"),
					"",
					`<div class="al-dispatch-chart" data-chart="customer"></div>`
				)}
			</div>
			<div class="al-dispatch-grid al-dispatch-grid-2" style="margin-top:14px">
				${utils.panel(
					__("Daily Trip Volume"),
					"",
					`<div class="al-dispatch-chart" data-chart="volume"></div>`
				)}
				${utils.panel(
					__("Document Verification"),
					"",
					`<div class="al-dispatch-chart" data-chart="verification"></div>`
				)}
			</div>
			<div style="margin-top:14px">
				${utils.panel(__("Driver Performance"), "", `<div data-driver-table></div>`)}
			</div>
			<div style="margin-top:14px">
				${utils.panel(__("Trip Detail"), __("Most recent trips in range"), `<div data-trip-table></div>`)}
			</div>
		`);

		this.render_charts(data);
		this.load_tables();
	},

	total_card(label, rows) {
		const utils = dispatch_portal.utils;
		const total = (rows || []).reduce((sum, row) => sum + (row.count || 0), 0);
		return `<div class="al-dispatch-kpi">
			<span class="al-dispatch-kpi-label">${utils.escape(label)}</span>
			<span class="al-dispatch-kpi-value">${utils.format_number(total, 0)}</span>
		</div>`;
	},

	quantity_card(label, value) {
		const utils = dispatch_portal.utils;
		return `<div class="al-dispatch-kpi">
			<span class="al-dispatch-kpi-label">${utils.escape(label)}</span>
			<span class="al-dispatch-kpi-value">${utils.format_number(value)}</span>
		</div>`;
	},

	render_charts(data) {
		const utils = dispatch_portal.utils;
		const me = this;

		const status = (data.trips_by_status || []).map((row) => ({
			label: String(row.label).replace(/_/g, " "),
			value: row.count,
		}));
		if (status.length) {
			this.charts.push(
				this.make_chart("[data-chart=status]", status, "bar", __("Trips"))
			);
		} else {
			this.$body.find("[data-chart=status]").html(utils.empty_state(__("No data")));
		}

		const customers = (data.trips_by_customer || []).map((row) => ({
			label: row.label,
			value: row.count,
		}));
		if (customers.length) {
			this.charts.push(this.make_chart("[data-chart=customer]", customers, "bar", __("Trips")));
		} else {
			this.$body.find("[data-chart=customer]").html(utils.empty_state(__("No data")));
		}

		const volume = (data.daily_trip_volume || []).map((row) => ({
			label: row.date,
			value: row.count,
		}));
		if (volume.length) {
			this.charts.push(this.make_chart("[data-chart=volume]", volume, "line", __("Trips")));
		} else {
			this.$body.find("[data-chart=volume]").html(utils.empty_state(__("No data")));
		}

		const verification = [
			{label: __("Pending"), value: (data.document_verification || {}).pending_review || 0},
			{label: __("Approved"), value: (data.document_verification || {}).approved || 0},
			{label: __("Rejected"), value: (data.document_verification || {}).rejected || 0},
		];
		this.charts.push(
			this.make_chart("[data-chart=verification]", verification, "pie", __("Documents"))
		);
	},

	make_chart(selector, data, type, title) {
		const utils = dispatch_portal.utils;
		const parent = this.$body.find(selector);
		if (!parent.length) {
			return null;
		}
		const chart_data = {
			labels: data.map((row) => String(row.label)),
			datasets: [{name: title, values: data.map((row) => row.value)}],
		};
		try {
			return new frappe.Chart(parent[0], {
				data: chart_data,
				type: type,
				height: 240,
				colors: type === "pie" ? ["#F59E0B", "#16A34A", "#DC2626"] : ["#0E7C86"],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: true,
				},
			});
		} catch (error) {
			parent.html(utils.empty_state(__("Chart could not be rendered.")));
			return null;
		}
	},

	load_tables() {
		const me = this;
		const range = this.range();
		const utils = dispatch_portal.utils;

		frappe
			.call({
				method: "dispatch_portal.api.reports.get_driver_report",
				args: {from_date: range.from_date, to_date: range.to_date},
				freeze: false,
			})
			.then((response) => {
				const rows = (response.message || {}).rows || [];
				me.$body.find("[data-driver-table]").html(
					rows.length
						? utils.table_html(
								[
									{label: __("Driver")},
									{label: __("Trips"), numeric: true},
									{label: __("Delivered Quantity"), numeric: true},
								],
								rows.map((row) => [
									utils.text(row.driver),
									utils.format_number(row.trips, 0),
									utils.format_number(row.delivered_quantity),
								])
						  )
						: utils.empty_state(__("No driver activity in this range."))
				);
			})
			.catch(() => {});

		frappe
			.call({
				method: "dispatch_portal.api.reports.get_trip_report",
				args: {from_date: range.from_date, to_date: range.to_date, limit: 200},
				freeze: false,
			})
			.then((response) => {
				const rows = (response.message || {}).rows || [];
				me.trip_rows = rows;
				me.$body.find("[data-trip-table]").html(
					rows.length
						? utils.table_html(
								[
									{label: __("Trip")},
									{label: __("Date")},
									{label: __("Status")},
									{label: __("Customer")},
									{label: __("Vehicle")},
									{label: __("Driver")},
									{label: __("Delivered"), numeric: true},
								],
								rows.map((row) => [
									utils.escape(row.trip),
									utils.format_date(row.trip_date),
									utils.status_badge(row.status),
									utils.text(row.customer),
									utils.text(row.vehicle),
									utils.text(row.driver),
									utils.format_number(row.delivered_quantity),
								])
						  )
						: utils.empty_state(__("No trips in this range."))
				);
			})
			.catch(() => {});
	},

	export_csv() {
		const rows = this.trip_rows || [];
		if (!rows.length) {
			frappe.msgprint(__("There are no trips to export in the selected range."));
			return;
		}

		const columns = [
			["trip", __("Trip")],
			["trip_date", __("Date")],
			["status", __("Status")],
			["transport_job", __("Transport Job")],
			["customer", __("Customer")],
			["loading_site", __("Loading Site")],
			["unloading_site", __("Unloading Site")],
			["material", __("Material")],
			["planned_quantity", __("Planned Quantity")],
			["delivered_quantity", __("Delivered Quantity")],
			["vehicle", __("Vehicle")],
			["driver", __("Driver")],
			["execution_source", __("Execution Source")],
			["transport_billing_status", __("Billing Status")],
		];

		const csv = [columns.map((column) => column[1])]
			.concat(
				rows.map((row) =>
					columns
						.map((column) => {
							const value = row[column[0]];
							const text = value === null || value === undefined ? "" : String(value);
							return `"${text.replace(/"/g, '""')}"`;
						})
						.join(",")
				)
			)
			.join("\n");

		const range = this.range();
		const filename = `al-rana-dispatch-trips_${range.from_date || "start"}_${range.to_date || "end"}.csv`;
		frappe.tools.downloadify(csv, null, filename);
	},
};
