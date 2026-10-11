// Dashboard section of the AL RANA Dispatch console.

frappe.provide("dispatch_portal.views");

dispatch_portal.views.dashboard = {
	render(context) {
		this.container = context.container;
		this.console = context.console;
		this.permissions = context.permissions || {};

		context.console.set_actions([
			{
				label: __("Refresh"),
				icon: "rotate-cw",
				onClick: () => this.load(),
			},
			{
				label: __("Verification"),
				icon: "check",
				primary: this.permissions.is_verifier,
				onClick: () => this.console.navigate("verification"),
			},
		]);

		this.load();
	},

	load() {
		const me = this;
		this.console.show_loading(__("Loading dispatcher dashboard"));
		this.console
			.call({
				method: "dispatch_portal.api.dashboard.get_dashboard",
			})
			.then((response) => me.render_body(response.message || {}))
			.catch((error) => this.console.show_error(error));
	},

	render_body(data) {
		const utils = dispatch_portal.utils;
		const kpis = data.kpis || {};
		const html = `
			<div class="al-dispatch-kpis">
				${this.kpi(__("Trips Today"), kpis.trips_today, __("Trips planned for today"), "")}
				${this.kpi(__("Planned"), kpis.planned, __("Awaiting assignment"), "tone-teal")}
				${this.kpi(__("Assigned"), kpis.assigned, __("Vehicle and driver set"), "")}
				${this.kpi(__("In Transit"), kpis.in_transit, __("On the road now"), "tone-teal")}
				${this.kpi(__("POD Pending"), kpis.pod_pending, __("Delivered, POD outstanding"), "tone-amber")}
				${this.kpi(__("Exceptions"), kpis.exception, __("Needs dispatcher action"), "tone-danger")}
				${this.kpi(__("Active Jobs"), kpis.active_jobs, __("Transport jobs in progress"), "")}
				${this.kpi(__("Available Trucks"), kpis.available_trucks, __("Idle and enabled"), "")}
				${this.kpi(__("Active Drivers"), kpis.active_drivers, __("Active driver records"), "")}
			</div>
			${utils.panel(
				__("Pipeline"),
				__("Trips by workflow status"),
				`<div class="al-dispatch-chips">${this.status_chips(data.status_breakdown)}</div>`
			)}
			<div class="al-dispatch-split">
				${utils.panel(
					__("Live Trips"),
					__("Planned, assigned, loaded and in transit"),
					this.trip_cards(data.active_trips),
					"al-dispatch-panel-live"
				)}
				<div>
					${utils.panel(
						__("Needs Attention"),
						__("Exceptions, delivered and unbilled trips"),
						this.attention_list(data.attention_trips)
					)}
					${this.verification_panel(data.verification)}
					${utils.panel(
						__("POD Backlog"),
						__("Delivered trips still awaiting a POD"),
						this.pod_list(data.pending_pod)
					)}
				</div>
			</div>
		`;

		this.container.html(html);
		this.bind_events();
	},

	kpi(label, value, hint, tone) {
		return `<div class="al-dispatch-kpi ${tone}">
			<span class="al-dispatch-kpi-label">${dispatch_portal.utils.escape(label)}</span>
			<span class="al-dispatch-kpi-value">${dispatch_portal.utils.format_number(value, 0)}</span>
			<span class="al-dispatch-kpi-hint">${dispatch_portal.utils.escape(hint)}</span>
		</div>`;
	},

	status_chips(breakdown) {
		if (!breakdown || !breakdown.length) {
			return dispatch_portal.utils.empty_state(__("No trips recorded yet."));
		}
		return breakdown
			.map(
				(row) =>
					`<span class="al-dispatch-chip">${dispatch_portal.utils.escape(
						String(row.status).replace(/_/g, " ")
					)}<span class="al-dispatch-chip-count">${dispatch_portal.utils.format_number(
						row.count,
						0
					)}</span></span>`
			)
			.join("");
	},

	trip_cards(trips) {
		const utils = dispatch_portal.utils;
		if (!trips || !trips.length) {
			return utils.empty_state(__("No active trips right now."));
		}
		return `<div class="al-dispatch-board">${trips
			.map(
				(trip) => `<article class="al-dispatch-card" data-trip="${utils.escape(trip.trip)}">
					<div class="al-dispatch-card-head">
						<span class="al-dispatch-card-trip">${utils.escape(trip.trip)}</span>
						${utils.status_badge(trip.status)}
					</div>
					<div class="al-dispatch-card-route">${utils.text(trip.route)}</div>
					<div class="al-dispatch-card-meta">
						<span>${__("Customer")}: ${utils.text(trip.customer)}</span>
						<span>${__("Vehicle")}: ${utils.text(trip.vehicle)}</span>
						<span>${__("Driver")}: ${utils.text(trip.driver)}</span>
						<span>${__("Qty")}: ${utils.format_number(trip.planned_quantity)} ${
					trip.uom ? utils.escape(trip.uom) : ""
				}</span>
					</div>
				</article>`
			)
			.join("")}</div>`;
	},

	attention_list(trips) {
		const utils = dispatch_portal.utils;
		if (!trips || !trips.length) {
			return utils.empty_state(__("Nothing needs attention."));
		}
		const rows = trips.map((trip) => [
			`<a class="al-dispatch-link" data-trip="${utils.escape(trip.trip)}">${utils.escape(trip.trip)}</a>`,
			utils.status_badge(trip.status),
			utils.text(trip.route),
			`<span class="al-dispatch-muted">${utils.format_datetime(trip.modified)}</span>`,
		]);
		return utils.table_html(
			[
				{label: __("Trip")},
				{label: __("Status")},
				{label: __("Route")},
				{label: __("Updated")},
			],
			rows
		);
	},

	verification_panel(summary) {
		const utils = dispatch_portal.utils;
		if (!this.permissions.is_verifier) {
			return "";
		}
		const data = summary || {};
		const body = `<div class="al-dispatch-chips">
			<span class="al-dispatch-chip">${__("Pending review")}<span class="al-dispatch-chip-count">${utils.format_number(
			data.pending_review,
			0
		)}</span></span>
			<span class="al-dispatch-chip">${__("Approved")}<span class="al-dispatch-chip-count">${utils.format_number(
			data.approved,
			0
		)}</span></span>
			<span class="al-dispatch-chip">${__("Rejected")}<span class="al-dispatch-chip-count">${utils.format_number(
			data.rejected,
			0
		)}</span></span>
		</div>
		<p style="margin:12px 0 0">
			<a class="al-dispatch-link" data-nav="verification">${__("Open the verification queue")}</a>
		</p>`;
		return utils.panel(__("Document Verification"), __("AI extraction review backlog"), body);
	},

	pod_list(trips) {
		const utils = dispatch_portal.utils;
		if (!trips || !trips.length) {
			return utils.empty_state(__("No trips are waiting for a POD."));
		}
		const rows = trips.map((trip) => [
			`<a class="al-dispatch-link" data-trip="${utils.escape(trip.trip)}">${utils.escape(trip.trip)}</a>`,
			utils.text(trip.vehicle),
			utils.format_number(trip.delivered_quantity),
			`<span class="al-dispatch-muted">${utils.format_datetime(trip.delivery_datetime)}</span>`,
		]);
		return utils.table_html(
			[
				{label: __("Trip")},
				{label: __("Vehicle")},
				{label: __("Delivered"), numeric: true},
				{label: __("Delivered At")},
			],
			rows
		);
	},

	bind_events() {
		const me = this;
		this.container.find("[data-trip]").on("click", function () {
			me.console.navigate("trips", $(this).attr("data-trip"));
		});
		this.container.find("[data-nav]").on("click", function () {
			me.console.navigate($(this).attr("data-nav"));
		});
	},
};
