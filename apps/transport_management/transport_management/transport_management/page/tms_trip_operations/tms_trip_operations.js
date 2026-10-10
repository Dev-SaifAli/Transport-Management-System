frappe.pages["tms-trip-operations"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Transport Operations"),
		single_column: true,
	});

	const state = {
		data: null,
	};

	page.set_primary_action(__("Refresh"), () => load_dashboard(), "refresh");

	$(page.body).html(`
		<div class="tms-operations-dashboard">
			<div class="tms-ops-loading">
				<div class="tms-ops-loading-line"></div>
				<div class="tms-ops-loading-line short"></div>
			</div>
		</div>
	`);

	const $root = $(page.body).find(".tms-operations-dashboard");
	ensure_tms_operations_styles();
	load_dashboard();

	function load_dashboard() {
		render_loading();
		frappe.call({
			method: "transport_management.tms_dashboard.get_trip_operations_dashboard",
			freeze: false,
			callback(r) {
				state.data = r.message || {};
				render_dashboard();
			},
			error() {
				render_error();
			},
		});
	}

	function render_loading() {
		$root.html(`
			<div class="tms-ops-loading">
				<div class="tms-ops-loading-line"></div>
				<div class="tms-ops-loading-line short"></div>
			</div>
		`);
	}

	function render_error() {
		$root.html(`
			<div class="tms-ops-state tms-ops-error">
				<div class="tms-ops-state-title">${__("Unable to load Transport Operations")}</div>
				<div class="tms-ops-state-text">${__("Please refresh or contact your Transport Admin if the issue continues.")}</div>
				<button class="btn btn-default btn-sm" data-action="reload-dashboard">${__("Try Again")}</button>
			</div>
		`);
		$root.find('[data-action="reload-dashboard"]').on("click", () => load_dashboard());
	}

	function render_dashboard() {
		const data = state.data || {};
		$root.html(`
			<section class="tms-ops-hero">
				<div class="tms-ops-title-wrap">
					<div class="tms-ops-mark" aria-hidden="true">${tms_icon("truck", "md")}</div>
					<div>
						<h1>${__("Transport Operations")}</h1>
						<div class="tms-ops-brand">${escape_html(data.brand || "AL RANA TRANSPORT LLC")}</div>
						<div class="tms-ops-subtitle">${__("Operational overview and daily trip activity")}</div>
					</div>
				</div>
				<div class="tms-ops-meta">
					<div>${format_date(data.today)}</div>
					<div>${escape_html((data.user && data.user.full_name) || frappe.session.user || "")}</div>
				</div>
			</section>

			<section class="tms-ops-kpis">
				${render_kpi("today", __("Today's Trips"), data.kpis && data.kpis.today, { trip_date: ["=", data.today] }, "calendar")}
				${render_kpi("planned", __("Planned"), data.kpis && data.kpis.planned, { status: "PLANNED" }, "calendar-clock")}
				${render_kpi("in_transit", __("In Transit"), data.kpis && data.kpis.in_transit, { status: "IN_TRANSIT" }, "route")}
				${render_kpi("pod_pending", __("POD Pending"), data.kpis && data.kpis.pod_pending, { status: "DELIVERED" }, "file-check")}
			</section>

			<section class="tms-ops-section tms-ops-actions-section">
				<div class="tms-ops-section-header">
					<div>
						<h2>${__("Quick Actions")}</h2>
					</div>
				</div>
				<div class="tms-ops-actions">
					${render_quick_actions(data.permissions || {})}
				</div>
			</section>

			<section class="tms-ops-section">
				<div class="tms-ops-section-header">
					<div>
						<h2>${__("Active Trips")}</h2>
						<p>${__("Recent active transport movements")}</p>
					</div>
					<button class="btn btn-default btn-sm tms-ops-icon-button" data-action="view-all-trips">
						<span>${__("View All")}</span>${tms_icon("right", "xs")}
					</button>
				</div>
				${render_trip_table(data.active_trips || [], false)}
			</section>

			<section class="tms-ops-section">
				<div class="tms-ops-section-header">
					<div>
						<h2>${__("Trips Requiring Attention")}</h2>
						<p>${__("Exceptions and delivered Trips awaiting POD")}</p>
					</div>
				</div>
				${render_trip_table(data.attention_trips || [], true)}
			</section>
		`);

		bind_actions();
	}

	function render_kpi(key, label, value, filters, icon) {
		return `
			<button class="tms-ops-kpi" data-kpi="${key}" data-filters='${escape_attr(JSON.stringify(filters))}'>
				<span class="tms-ops-kpi-icon" aria-hidden="true">${tms_icon(icon, "sm")}</span>
				<span class="tms-ops-kpi-label">${escape_html(label)}</span>
				<strong>${cint(value || 0).toLocaleString()}</strong>
			</button>
		`;
	}

	function render_quick_actions(permissions) {
		const actions = [];
		if (permissions.can_create_trip) {
			actions.push(`<button class="btn btn-primary btn-sm tms-ops-icon-button" data-action="new-trip">${tms_icon("plus", "xs")}<span>${__("New Trip")}</span></button>`);
		}
		if (permissions.can_read_job) {
			actions.push(`<button class="btn btn-default btn-sm tms-ops-icon-button" data-action="transport-jobs">${tms_icon("briefcase", "xs")}<span>${__("Transport Jobs")}</span></button>`);
		}
		if (permissions.can_read_trip) {
			actions.push(`<button class="btn btn-default btn-sm tms-ops-icon-button" data-action="all-trips">${tms_icon("truck", "xs")}<span>${__("All Trips")}</span></button>`);
		}
		if (!actions.length) {
			return `<div class="tms-ops-empty-inline">${__("No quick actions are available for your current permissions.")}</div>`;
		}
		return actions.join("");
	}

	function render_trip_table(rows, show_issue) {
		if (!rows.length) {
			const icon = show_issue ? "circle-check" : "truck";
			const title = show_issue ? __("All clear") : __("No active trips");
			const text = show_issue
				? __("No trips currently require attention.")
				: __("Active transport movements will appear here.");
			return `
				<div class="tms-ops-empty">
					<div class="tms-ops-empty-icon" aria-hidden="true">${tms_icon(icon, "md")}</div>
					<div>
						<div class="tms-ops-empty-title">${title}</div>
						<div class="tms-ops-empty-text">${text}</div>
					</div>
				</div>
			`;
		}

		return `
			<div class="tms-ops-table-wrap">
				<table class="tms-ops-table">
					<thead>
						<tr>
							<th>${__("Trip")}</th>
							<th>${__("Customer")}</th>
							<th>${__("Route")}</th>
							<th>${__("Vehicle")}</th>
							<th>${__("Driver")}</th>
							${show_issue ? `<th>${__("Issue")}</th>` : ""}
							<th>${__("Status")}</th>
							<th>${__("Updated")}</th>
						</tr>
					</thead>
					<tbody>
						${rows.map((row) => render_trip_row(row, show_issue)).join("")}
					</tbody>
				</table>
			</div>
		`;
	}

	function render_trip_row(row, show_issue) {
		return `
			<tr class="tms-ops-trip-row" data-trip="${escape_attr(row.trip || "")}">
				<td><button class="tms-ops-link" data-trip-link="${escape_attr(row.trip || "")}">${escape_html(row.trip || "")}</button></td>
				<td><span title="${escape_attr(row.customer || "")}">${escape_html(row.customer || "")}</span></td>
				<td><span title="${escape_attr(row.route || "")}">${escape_html(row.route || "")}</span></td>
				<td><span title="${escape_attr(row.vehicle || "")}">${escape_html(row.vehicle || "")}</span></td>
				<td><span title="${escape_attr(row.driver || "")}">${escape_html(row.driver || "")}</span></td>
				${show_issue ? `<td>${escape_html(row.issue || "")}</td>` : ""}
				<td>${status_badge(row.status)}</td>
				<td><span title="${escape_attr(row.updated || "")}">${format_updated(row.updated)}</span></td>
			</tr>
		`;
	}

	function bind_actions() {
		$root.find("[data-kpi]").on("click", function () {
			const filters = JSON.parse($(this).attr("data-filters") || "{}");
			open_trip_list(filters);
		});
		$root.find('[data-action="new-trip"]').on("click", () => frappe.new_doc("Transport Trip"));
		$root.find('[data-action="transport-jobs"]').on("click", () => frappe.set_route("List", "Transport Job"));
		$root.find('[data-action="all-trips"], [data-action="view-all-trips"]').on("click", () => frappe.set_route("List", "Transport Trip"));
		$root.find("[data-trip-link], .tms-ops-trip-row").on("click", function (event) {
			const trip = $(this).attr("data-trip-link") || $(this).attr("data-trip");
			if (trip) {
				event.preventDefault();
				frappe.set_route("Form", "Transport Trip", trip);
			}
		});
	}

	function open_trip_list(filters) {
		frappe.route_options = filters || {};
		frappe.set_route("List", "Transport Trip");
	}
};

function status_badge(status) {
	const value = status || "";
	const color = {
		PLANNED: "gray",
		ASSIGNED: "blue",
		LOADED: "orange",
		IN_TRANSIT: "purple",
		DELIVERED: "green",
		POD_RECEIVED: "teal",
		CLOSED: "dark",
		CANCELLED: "red",
		EXCEPTION: "orange",
	}[value] || "gray";
	return `<span class="tms-ops-badge tms-${color}">${escape_html(__(value))}</span>`;
}

function format_date(value) {
	return value ? frappe.datetime.str_to_user(value, false, true) : "";
}

function format_updated(value) {
	return value ? frappe.datetime.comment_when(value, true) : "";
}

function escape_html(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
}

function escape_attr(value) {
	return escape_html(value).replace(/"/g, "&quot;");
}

function tms_icon(icon, size) {
	return frappe.utils.icon(icon, size || "sm");
}

function ensure_tms_operations_styles() {
	if (document.getElementById("tms-operations-dashboard-styles")) {
		return;
	}

	$(`
		<style id="tms-operations-dashboard-styles">
			.tms-operations-dashboard {
				color: var(--text-color);
				margin: 0 auto;
				max-width: 1360px;
				padding: 6px 0 28px;
			}
			.tms-ops-hero {
				align-items: center;
				background: var(--card-bg);
				border: 1px solid var(--border-color);
				border-radius: 8px;
				display: flex;
				justify-content: space-between;
				margin-bottom: 16px;
				padding: 16px 18px;
			}
			.tms-ops-title-wrap {
				align-items: center;
				display: flex;
				gap: 13px;
				min-width: 0;
			}
			.tms-ops-mark {
				align-items: center;
				background: var(--blue-50);
				border: 1px solid var(--blue-100);
				border-radius: 8px;
				color: var(--blue-600);
				display: inline-flex;
				flex: 0 0 42px;
				height: 42px;
				justify-content: center;
				width: 42px;
			}
			.tms-ops-brand {
				color: var(--text-muted);
				font-size: 12px;
				font-weight: 600;
				letter-spacing: 0;
				text-transform: uppercase;
			}
			.tms-ops-hero h1 {
				font-size: 26px;
				font-weight: 700;
				line-height: 1.2;
				margin: 0 0 3px;
			}
			.tms-ops-subtitle,
			.tms-ops-meta,
			.tms-ops-section-header p {
				color: var(--text-muted);
				font-size: 13px;
			}
			.tms-ops-meta {
				line-height: 1.6;
				text-align: right;
				white-space: nowrap;
			}
			.tms-ops-kpis {
				display: grid;
				gap: 12px;
				grid-template-columns: repeat(4, minmax(180px, 240px));
				justify-content: start;
				margin-bottom: 16px;
			}
			.tms-ops-kpi {
				background: var(--card-bg);
				border: 1px solid var(--border-color);
				border-left: 3px solid var(--blue-400);
				border-radius: 8px;
				box-shadow: var(--shadow-xs);
				cursor: pointer;
				min-height: 116px;
				padding: 15px 16px;
				text-align: left;
				transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
				width: 100%;
			}
			.tms-ops-kpi:hover {
				border-color: var(--gray-400);
				box-shadow: var(--shadow-sm);
				transform: translateY(-1px);
			}
			.tms-ops-kpi[data-kpi="planned"] {
				border-left-color: var(--blue-300);
			}
			.tms-ops-kpi[data-kpi="in_transit"] {
				border-left-color: var(--purple-400);
			}
			.tms-ops-kpi[data-kpi="pod_pending"] {
				border-left-color: var(--orange-400);
			}
			.tms-ops-kpi-icon {
				align-items: center;
				background: var(--control-bg);
				border-radius: 7px;
				color: var(--blue-600);
				display: inline-flex;
				height: 30px;
				justify-content: center;
				margin-bottom: 10px;
				width: 30px;
			}
			.tms-ops-kpi[data-kpi="in_transit"] .tms-ops-kpi-icon {
				color: var(--purple-600);
			}
			.tms-ops-kpi[data-kpi="pod_pending"] .tms-ops-kpi-icon {
				color: var(--orange-700);
			}
			.tms-ops-kpi-label {
				color: var(--text-muted);
				display: block;
				font-size: 12px;
				font-weight: 600;
				margin-bottom: 8px;
				text-transform: uppercase;
			}
			.tms-ops-kpi strong {
				display: block;
				font-size: 31px;
				font-variant-numeric: tabular-nums;
				line-height: 1;
			}
			.tms-ops-section {
				background: var(--card-bg);
				border: 1px solid var(--border-color);
				border-radius: 8px;
				margin-bottom: 16px;
				padding: 16px;
			}
			.tms-ops-actions-section {
				max-width: 640px;
				padding: 14px 16px;
			}
			.tms-ops-section-header {
				align-items: center;
				display: flex;
				justify-content: space-between;
				gap: 12px;
				margin-bottom: 12px;
			}
			.tms-ops-section-header h2 {
				font-size: 16px;
				font-weight: 700;
				margin: 0;
			}
			.tms-ops-section-header p {
				margin: 3px 0 0;
			}
			.tms-ops-actions {
				display: flex;
				flex-wrap: wrap;
				gap: 8px;
			}
			.tms-ops-icon-button {
				align-items: center;
				display: inline-flex;
				gap: 6px;
			}
			.tms-ops-table-wrap {
				overflow-x: auto;
			}
			.tms-ops-table {
				border-collapse: collapse;
				font-size: 13px;
				min-width: 900px;
				width: 100%;
			}
			.tms-ops-table th {
				border-bottom: 1px solid var(--border-color);
				color: var(--text-muted);
				font-size: 11px;
				font-weight: 700;
				padding: 7px 10px;
				text-align: left;
				text-transform: uppercase;
			}
			.tms-ops-table td {
				border-bottom: 1px solid var(--border-color);
				max-width: 190px;
				overflow: hidden;
				padding: 8px 10px;
				text-overflow: ellipsis;
				vertical-align: middle;
				white-space: nowrap;
			}
			.tms-ops-trip-row {
				cursor: pointer;
			}
			.tms-ops-trip-row:hover {
				background: var(--control-bg);
			}
			.tms-ops-link {
				background: none;
				border: 0;
				color: var(--link-color);
				font-weight: 600;
				padding: 0;
			}
			.tms-ops-badge {
				border-radius: 999px;
				display: inline-block;
				font-size: 11px;
				font-weight: 700;
				line-height: 1;
				padding: 4px 7px;
				white-space: nowrap;
			}
			.tms-ops-badge.tms-blue { background: var(--blue-50); color: var(--blue-700); }
			.tms-ops-badge.tms-orange { background: var(--orange-50); color: var(--orange-700); }
			.tms-ops-badge.tms-green { background: var(--green-50); color: var(--green-700); }
			.tms-ops-badge.tms-gray { background: var(--gray-100); color: var(--gray-700); }
			.tms-ops-badge.tms-red { background: var(--red-50); color: var(--red-700); }
			.tms-ops-badge.tms-purple { background: var(--purple-50); color: var(--purple-700); }
			.tms-ops-badge.tms-teal { background: var(--teal-50); color: var(--teal-700); }
			.tms-ops-badge.tms-dark { background: var(--gray-200); color: var(--gray-800); }
			.tms-ops-empty,
			.tms-ops-empty-inline,
			.tms-ops-state {
				border: 1px dashed var(--border-color);
				border-radius: 8px;
				color: var(--text-muted);
				padding: 14px 16px;
			}
			.tms-ops-empty {
				align-items: center;
				display: flex;
				gap: 12px;
			}
			.tms-ops-empty-icon {
				align-items: center;
				background: var(--green-50);
				border-radius: 8px;
				color: var(--green-600);
				display: inline-flex;
				height: 34px;
				justify-content: center;
				width: 34px;
			}
			.tms-ops-empty-title {
				color: var(--text-color);
				font-size: 14px;
				font-weight: 700;
				margin-bottom: 2px;
			}
			.tms-ops-empty-text {
				font-size: 13px;
			}
			.tms-ops-state {
				background: var(--card-bg);
				margin-top: 8px;
			}
			.tms-ops-state-title {
				color: var(--text-color);
				font-size: 16px;
				font-weight: 700;
				margin-bottom: 4px;
			}
			.tms-ops-state-text {
				margin-bottom: 12px;
			}
			.tms-ops-loading {
				background: var(--card-bg);
				border: 1px solid var(--border-color);
				border-radius: 8px;
				padding: 20px;
			}
			.tms-ops-loading-line {
				animation: tms-pulse 1.2s ease-in-out infinite;
				background: var(--control-bg);
				border-radius: 4px;
				height: 14px;
				margin-bottom: 10px;
				width: 70%;
			}
			.tms-ops-loading-line.short {
				width: 42%;
			}
			@keyframes tms-pulse {
				0%, 100% { opacity: 0.55; }
				50% { opacity: 1; }
			}
			@media (max-width: 991px) {
				.tms-ops-kpis {
					grid-template-columns: repeat(2, minmax(180px, 240px));
				}
				.tms-ops-hero {
					flex-direction: column;
					align-items: flex-start;
				}
				.tms-ops-meta {
					margin-top: 10px;
					text-align: left;
				}
			}
			@media (max-width: 575px) {
				.tms-ops-kpis {
					grid-template-columns: minmax(0, 1fr);
				}
				.tms-ops-section-header {
					align-items: flex-start;
					flex-direction: column;
				}
				.tms-ops-title-wrap {
					align-items: flex-start;
				}
				.tms-ops-hero h1 {
					font-size: 23px;
				}
			}
		</style>
	`).appendTo("head");
}
