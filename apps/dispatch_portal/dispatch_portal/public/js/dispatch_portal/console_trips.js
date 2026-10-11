// Trips section of the AL RANA Dispatch console.

frappe.provide("dispatch_portal.views");

dispatch_portal.views.trips = {
	state: {
		filters: {status: "", from_date: "", to_date: "", search: "", customer: ""},
		start: 0,
		page_length: 25,
		total: 0,
		selected: null,
		statuses: [],
	},

	render(context) {
		this.container = context.container;
		this.console = context.console;
		this.permissions = context.permissions || {};
		this.state.selected = (frappe.get_route() || [])[2] || null;

		context.console.set_actions([
			{label: __("Refresh"), icon: "rotate-cw", onClick: () => this.load()},
			{
				label: __("New Trip"),
				icon: "circle-plus",
				primary: true,
				onClick: () => this.open_new_trip(),
			},
			{
				label: __("Trip Map"),
				icon: "map",
				onClick: () => this.console.navigate("trip-map"),
			},
		]);

		this.render_filters();
		this.load();
	},

	open_new_trip() {
		if (!this.permissions.can_create_transport_trip) {
			frappe.msgprint(__("You do not have permission to create a Transport Trip."));
			return;
		}
		frappe.set_route("Form", "Transport Trip", "new-transport-trip-1");
	},

	render_filters() {
		const utils = dispatch_portal.utils;
		const me = this;
		const filters = this.state.filters;

		const status_options = ["<option value=\"\">" + __("All statuses") + "</option>"]
			.concat(
				this.state.statuses.map(
					(row) =>
						`<option value="${utils.escape(row.value)}" ${
							filters.status === row.value ? "selected" : ""
						}>${utils.escape(row.label)}</option>`
				)
			)
			.join("");

		const html = `<form class="al-dispatch-filters" data-filter-form>
			<div class="al-dispatch-field">
				<label>${__("Search trip")}</label>
				<input type="text" name="search" value="${utils.escape(filters.search)}" placeholder="${__(
			"Trip name"
		)}" />
			</div>
			<div class="al-dispatch-field">
				<label>${__("Status")}</label>
				<select name="status">${status_options}</select>
			</div>
			<div class="al-dispatch-field">
				<label>${__("From date")}</label>
				<input type="date" name="from_date" value="${utils.escape(filters.from_date)}" />
			</div>
			<div class="al-dispatch-field">
				<label>${__("To date")}</label>
				<input type="date" name="to_date" value="${utils.escape(filters.to_date)}" />
			</div>
			<div class="al-dispatch-field">
				<label>${__("Customer")}</label>
				<input type="text" name="customer" value="${utils.escape(filters.customer)}" />
			</div>
			<div class="al-dispatch-filters-actions">
				<button type="button" class="btn btn-sm btn-primary" data-apply-filters>
					${frappe.utils.icon("funnel")}<span>${__("Apply")}</span>
				</button>
				<button type="button" class="btn btn-sm btn-default" data-reset-filters>
					${frappe.utils.icon("rotate-ccw")}<span>${__("Reset")}</span>
				</button>
			</div>
		</form>
		<div data-trips-table></div>
		<div data-trips-detail></div>`;

		this.container.html(html);
		this.$form = this.container.find("[data-filter-form]");
		this.$table = this.container.find("[data-trips-table]");
		this.$detail = this.container.find("[data-trips-detail]");

		this.container.find("[data-apply-filters]").on("click", () => this.apply_filters());
		this.container.find("[data-reset-filters]").on("click", () => this.reset_filters());
		this.$form.on("submit", (event) => {
			event.preventDefault();
			this.apply_filters();
		});
	},

	apply_filters() {
		const values = this.$form.serializeArray();
		this.state.filters = {};
		values.forEach((row) => {
			this.state.filters[row.name] = row.value;
		});
		this.state.start = 0;
		this.load();
	},

	reset_filters() {
		this.state.filters = {status: "", from_date: "", to_date: "", search: "", customer: ""};
		this.state.start = 0;
		this.render_filters();
		this.load();
	},

	load() {
		const me = this;
		this.console.show_loading(__("Loading trips"));
		if (!this.state.statuses.length) {
			frappe
				.call({method: "dispatch_portal.api.trips.get_status_flow", freeze: false})
				.then((response) => {
					me.state.statuses = (response.message || {}).statuses || [];
					me.render_filters();
					me.fetch_trips();
				})
				.catch(() => me.fetch_trips());
			return;
		}
		this.fetch_trips();
	},

	fetch_trips() {
		const me = this;
		this.console
			.call({
				method: "dispatch_portal.api.trips.get_trips",
				args: {
					filters: this.state.filters,
					start: this.state.start,
					page_length: this.state.page_length,
				},
			})
			.then((response) => me.render_trips(response.message || {}))
			.catch((error) => this.console.show_error(error));
	},

	render_trips(data) {
		const utils = dispatch_portal.utils;
		const trips = data.trips || [];
		this.state.total = data.total || 0;

		const rows = trips.map((trip) => [
			`<a class="al-dispatch-link" data-trip="${utils.escape(trip.trip)}">${utils.escape(trip.trip)}</a>`,
			utils.format_date(trip.trip_date),
			utils.status_badge(trip.status),
			utils.text(trip.customer),
			utils.text(trip.route),
			utils.text(trip.vehicle),
			utils.text(trip.driver),
			utils.format_number(trip.planned_quantity),
			`<span class="al-dispatch-muted">${utils.format_datetime(trip.modified)}</span>`,
			`<button type="button" class="btn btn-xs btn-default" data-detail="${utils.escape(
				trip.trip
			)}">${__("Open")}</button>`,
		]);

		const header = [
			{label: __("Trip")},
			{label: __("Date")},
			{label: __("Status")},
			{label: __("Customer")},
			{label: __("Route")},
			{label: __("Vehicle")},
			{label: __("Driver")},
			{label: __("Planned"), numeric: true},
			{label: __("Updated")},
			{label: __("Actions"), actions: true},
		];

		const body = rows.length
			? utils.table_html(header, rows)
			: utils.empty_state(__("No trips match the current filters."));

		this.$table.html(body + this.render_pagination());

		this.$table.find("[data-trip]").on("click", (event) => {
			this.open_detail($(event.currentTarget).attr("data-trip"));
		});
		this.$table.find("[data-detail]").on("click", (event) => {
			this.open_detail($(event.currentTarget).attr("data-detail"));
		});
		this.$table.find("[data-page]").on("click", (event) => {
			this.state.start = Number($(event.currentTarget).attr("data-page"));
			this.fetch_trips();
		});
	},

	render_pagination() {
		const utils = dispatch_portal.utils;
		const start = this.state.start;
		const length = this.state.page_length;
		const shown = Math.min(start + length, this.state.total);
		const prev = Math.max(start - length, 0);
		const next = start + length < this.state.total ? start + length : null;

		return `<div class="al-dispatch-pagination">
			<span>${utils.format_number(start + (this.state.total ? 1 : 0), 0)} - ${utils.format_number(
			shown,
			0
		)} ${__("of")} ${utils.format_number(this.state.total, 0)}</span>
			<span class="al-dispatch-pagination-buttons">
				<button type="button" class="btn btn-xs btn-default" data-page="${prev}" ${
			start === 0 ? "disabled" : ""
		}>${__("Previous")}</button>
				<button type="button" class="btn btn-xs btn-default" data-page="${next === null ? start : next}" ${
			next === null ? "disabled" : ""
		}>${__("Next")}</button>
			</span>
		</div>`;
	},

	open_detail(trip_name) {
		if (!trip_name) {
			return;
		}
		const me = this;
		this.$detail.html(
			`<div class="al-dispatch-loading" style="margin-top:14px">
				<span class="al-dispatch-spinner"></span><span>${__("Loading trip")}</span>
			</div>`
		);

		this.console
			.call({method: "dispatch_portal.api.trips.get_trip", args: {trip_id: trip_name}})
			.then((response) => me.render_detail(response.message || {}))
			.catch((error) => {
				me.$detail.html(
					`<div class="al-dispatch-error" style="margin-top:14px">${dispatch_portal.utils.server_message(
						error
					)}</div>`
				);
			});
	},

	render_detail(trip) {
		const utils = dispatch_portal.utils;
		const can_write = this.permissions.can_write_transport_trip;

		const detail_rows = [
			[__("Customer"), utils.text(trip.customer)],
			[__("Transport Job"), utils.text(trip.transport_job)],
			[__("Trip Date"), utils.format_date(trip.trip_date)],
			[__("Status"), utils.status_badge(trip.status)],
			[__("Loading Site"), utils.text(trip.loading_site)],
			[__("Unloading Site"), utils.text(trip.unloading_site)],
			[__("Material"), utils.text(trip.material)],
			[
				__("Planned Quantity"),
				`${utils.format_number(trip.planned_quantity)} ${utils.escape(trip.uom || "")}`,
			],
			[
				__("Loaded Quantity"),
				`${utils.format_number(trip.loaded_quantity)} ${utils.escape(trip.uom || "")}`,
			],
			[
				__("Delivered Quantity"),
				`${utils.format_number(trip.delivered_quantity)} ${utils.escape(trip.uom || "")}`,
			],
			[__("Loading Started"), utils.format_datetime(trip.loading_datetime)],
			[__("Driver Started"), utils.format_datetime(trip.driver_started_at)],
			[__("Delivered At"), utils.format_datetime(trip.delivery_datetime)],
			[__("GDN"), utils.text(trip.gdn)],
			[__("POD Received At"), utils.format_datetime(trip.pod_received_at)],
			[__("Billing Status"), utils.text(trip.transport_billing_status)],
			[
				__("Charges"),
				(trip.charges || [])
					.map(
						(charge) =>
							`${utils.escape(charge.charge_type)}: ${utils.format_number(charge.amount)}`
					)
					.join("<br>") || "<span class=\"al-dispatch-muted\">-</span>",
			],
			[__("Remarks"), utils.text(trip.remarks)],
		];

		const stops = (trip.loading_stops || [])
			.map(
				(stop) =>
					`<li>${utils.text(stop.loading_location)} &middot; ${utils.format_number(
						stop.planned_quantity
					)} ${utils.escape(trip.uom || "")}</li>`
			)
			.join("");

		const actions = can_write
			? `<div class="al-dispatch-filters-actions" style="margin:0">
					<button type="button" class="btn btn-sm btn-default" data-assign="${utils.escape(
						trip.trip
					)}">${__("Assign")}</button>
					<button type="button" class="btn btn-sm btn-default" data-transition="${utils.escape(
						trip.trip
					)}">${__("Change Status")}</button>
				</div>`
			: "";

		this.$detail.html(
			`<section class="al-dispatch-panel" style="margin-top:14px">
				<header class="al-dispatch-panel-head">
					<div>
						<h3 class="al-dispatch-panel-title">${utils.escape(trip.trip)}</h3>
						<p class="al-dispatch-panel-sub">${utils.escape(trip.route)}</p>
					</div>
					<div style="display:flex;align-items:center;gap:8px">
						${utils.status_badge(trip.status)}
						${actions}
					</div>
				</header>
				<div class="al-dispatch-panel-body">
					<div class="al-dispatch-split">
						${utils.table_html(
							[
								{label: __("Field")},
								{label: __("Value")},
							],
							detail_rows
						)}
						<div>
							${utils.panel(__("Loading Stops"), "", stops ? `<ul>${stops}</ul>` : utils.empty_state(__("No loading stops.")))}
							${utils.panel(
								__("Transport Job"),
								"",
								trip.job
									? utils.table_html(
											[
												{label: __("Field")},
												{label: __("Value")},
											],
											[
												[__("Job"), utils.text(trip.job.name)],
												[__("Status"), utils.status_badge(trip.job.status)],
												[__("Requested Quantity"), utils.format_number(trip.job.requested_quantity)],
												[__("Customer LPO"), utils.text(trip.job.customer_lpo_number)],
												[__("Instructions"), utils.text(trip.job.special_instructions)],
											]
									  )
									: utils.empty_state(__("No Transport Job linked."))
							)}
						</div>
					</div>
				</div>
			</section>`
		);

		this.$detail.find("[data-assign]").on("click", (event) => {
			this.open_assign_dialog($(event.currentTarget).attr("data-assign"));
		});
		this.$detail.find("[data-transition]").on("click", (event) => {
			this.open_transition_dialog($(event.currentTarget).attr("data-transition"), trip.status);
		});
	},

	open_assign_dialog(trip_name) {
		const me = this;
		frappe
			.call({
				method: "dispatch_portal.api.trips.get_assignment_options",
				args: {trip_id: trip_name},
			})
			.then((response) => {
				const data = response.message || {};
				const utils = dispatch_portal.utils;
				const truck_field = {
					label: __("Truck"),
					fieldname: "vehicle",
					fieldtype: "Select",
					options: ["", ...(data.trucks || []).map((row) => `${row.name} (${row.truck_number || "-"})`)],
				};
				const driver_field = {
					label: __("Driver"),
					fieldname: "driver",
					fieldtype: "Select",
					options: ["", ...(data.drivers || []).map((row) => `${row.name} (${row.full_name || "-"})`)],
				};

				const dialog = new frappe.ui.Dialog({
					title: __("Assign Trip"),
					fields: [truck_field, driver_field],
					primary_action_label: __("Assign"),
					primary_action: (values) => {
						const vehicle = (values.vehicle || "").split(" (")[0];
						const driver = (values.driver || "").split(" (")[0];
						frappe
							.call({
								method: "dispatch_portal.api.trips.assign_trip",
								args: {trip_id: trip_name, vehicle, driver},
								btn: dialog.get_primary_btn(),
							})
							.then(() => {
								dialog.hide();
								frappe.show_alert({message: __("Trip assigned"), indicator: "green"});
								me.fetch_trips();
								me.open_detail(trip_name);
							})
							.catch((error) => {
								frappe.msgprint(utils.server_message(error) || __("Assignment failed."));
							});
					},
				});
				dialog.show();
			})
			.catch((error) => dispatch_portal.utils.show_error(error));
	},

	open_transition_dialog(trip_name, current_status) {
		const me = this;
		const utils = dispatch_portal.utils;
		const field = {
			label: __("New Status"),
			fieldname: "status",
			fieldtype: "Select",
			options: this.state.statuses.map((row) => row.value).join("\n"),
			default: current_status,
		};
		const dialog = new frappe.ui.Dialog({
			title: __("Change Trip Status"),
			fields: [field],
			primary_action_label: __("Update"),
			primary_action: (values) => {
				frappe
					.call({
						method: "dispatch_portal.api.trips.transition_trip",
						args: {trip_id: trip_name, status: values.status},
						btn: dialog.get_primary_btn(),
					})
					.then(() => {
						dialog.hide();
						frappe.show_alert({message: __("Trip updated"), indicator: "green"});
						me.fetch_trips();
						me.open_detail(trip_name);
					})
					.catch((error) => frappe.msgprint(utils.server_message(error)));
			},
		});
		dialog.show();
	},
};
