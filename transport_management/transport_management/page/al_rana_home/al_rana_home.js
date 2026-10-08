frappe.pages["al-rana-home"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("AL RANA Home"),
		single_column: true,
	});

	const state = {
		collapsed: false,
		profile: get_default_profile(),
	};

	$(page.body).html(`<div class="arl-shell"></div>`);
	const $root = $(page.body).find(".arl-shell");
	const can_preview_roles = can_preview_al_rana_roles();

	ensure_al_rana_home_styles();
	safe_render();

	function safe_render() {
		try {
			render();
		} catch (error) {
			console.error("AL RANA Home render failed", error);
			render_error(error);
		}
	}

	function render() {
		const profile = get_profile(state.profile);
		$root.toggleClass("is-collapsed", state.collapsed);
		$root.html(`
			<aside class="arl-sidebar" aria-label="${escape_attr(__("AL RANA navigation"))}">
				${render_brand()}
				${render_nav(profile)}
				${render_user(profile)}
			</aside>
			<main class="arl-main">
				${render_topbar(profile)}
				${render_home(profile)}
			</main>
		`);
		bind_events();
	}

	function render_error(error) {
		const message = error && error.message ? error.message : __("Please reload the page.");
		$root.html(`
			<main class="arl-main arl-error-main">
				<div class="arl-panel arl-error-panel">
					<h2>${__("AL RANA Home could not load")}</h2>
					<p>${escape_html(message)}</p>
					<button class="btn btn-primary" type="button" data-action="reload-home">${__("Reload")}</button>
				</div>
			</main>
		`);
		$root.find('[data-action="reload-home"]').on("click", () => window.location.reload());
	}

	function render_brand() {
		return `
			<div class="arl-brand">
				<div class="arl-brand-mark" aria-hidden="true">AR</div>
				<div class="arl-brand-copy">
					<div class="arl-brand-name">${__("AL RANA")}</div>
					<div class="arl-brand-subtitle">${__("Transport Management System")}</div>
				</div>
			</div>
		`;
	}

	function render_nav(profile) {
		const sections = as_array(profile.sections);
		return `
			<nav class="arl-nav">
				${as_array(NAV_GROUPS).filter((group) => sections.includes(group.key))
					.map((group) => render_group(group, profile))
					.join("")}
			</nav>
		`;
	}

	function render_group(group, profile) {
		const is_dashboard = group.key === "dashboard";
		if (is_dashboard) {
			return render_nav_item(group, "is-root");
		}
		const items = as_array(group.items).filter((item) => {
			const allowed_profiles = as_array(item.profiles);
			return !allowed_profiles.length || allowed_profiles.includes(state.profile);
		});
		if (!items.length) {
			return "";
		}
		return `
			<div class="arl-nav-group" data-group="${escape_attr(group.key)}">
				<button class="arl-nav-parent" type="button" data-route="${escape_attr(group.route || "")}" title="${escape_attr(group.label)}">
					<span class="arl-nav-icon">${icon(group.icon)}</span>
					<span class="arl-nav-label">${escape_html(group.label)}</span>
				</button>
				<div class="arl-nav-children">
					${items.map((item) => render_nav_item(item)).join("")}
				</div>
			</div>
		`;
	}

	function render_nav_item(item, extra_class) {
		return `
			<button class="arl-nav-item ${extra_class || ""}" type="button" data-route="${escape_attr(item.route || "")}" title="${escape_attr(item.label)}">
				<span class="arl-nav-icon">${icon(item.icon)}</span>
				<span class="arl-nav-label">${escape_html(item.label)}</span>
			</button>
		`;
	}

	function render_user(profile) {
		const name = frappe.session.user_fullname || frappe.session.user || __("AL RANA User");
		return `
			<div class="arl-sidebar-footer">
				<button class="arl-collapse" type="button" data-action="toggle-sidebar">
					${icon(state.collapsed ? "sidebar" : "sidebar-collapse")}<span>${state.collapsed ? __("Expand") : __("Collapse")}</span>
				</button>
				<div class="arl-user">
					<div class="arl-avatar" aria-hidden="true">${get_initials(name)}</div>
					<div class="arl-user-copy">
						<div class="arl-user-name">${escape_html(name)}</div>
						<div class="arl-user-role">${escape_html(profile.label)}</div>
					</div>
				</div>
			</div>
		`;
	}

	function render_topbar(profile) {
		return `
			<header class="arl-topbar">
				<div>
					<div class="arl-breadcrumb">${__("AL RANA")} / ${escape_html(profile.label)}</div>
					<h1>${__("Home")}</h1>
				</div>
				<div class="arl-topbar-actions">
					<div class="arl-search" aria-label="${escape_attr(__("Global search"))}">
						${icon("search")}
						<span>${__("Search or open a page")}</span>
					</div>
					${can_preview_roles ? render_role_switcher() : ""}
				</div>
			</header>
		`;
	}

	function render_role_switcher() {
		const preview_profiles = Object.entries(ROLE_PROFILES).filter((entry) => entry[1] && entry[1].preview);
		return `
			<div class="arl-role-switcher" aria-label="${escape_attr(__("Role preview"))}">
				<span>${__("Preview only")}</span>
				${preview_profiles
					.map(([key, value]) => `
						<button class="${key === state.profile ? "active" : ""}" data-profile="${escape_attr(key)}" type="button">
							${escape_html(value.short)}
						</button>
					`).join("")}
			</div>
		`;
	}

	function render_home(profile) {
		const now = frappe.datetime.str_to_user(frappe.datetime.nowdate(), false, true);
		const actions = as_array(profile.actions);
		const kpis = as_array(profile.kpis);
		const sections = as_array(profile.sections);
		return `
			<section class="arl-hero">
				<div>
					<div class="arl-demo-label">${__("Demo UI data")}</div>
					<h2>${__("Good morning")}, ${escape_html(frappe.session.user_fullname || __("AL RANA Team"))}</h2>
					<p>${escape_html(profile.label)} · ${escape_html(now)}</p>
				</div>
				<div class="arl-hero-status">
					<span class="arl-status-dot"></span>
					${__("Internal office ERP/TMS")}
				</div>
			</section>

			<section class="arl-panel arl-actions-panel">
				<div class="arl-section-head">
					<div>
						<h3>${__("Quick Actions")}</h3>
						<p>${__("Role-aware shortcuts to common office tasks")}</p>
					</div>
				</div>
				<div class="arl-quick-actions">
					${as_array(QUICK_ACTIONS).filter((action) => actions.includes(action.key))
						.map(render_action)
						.join("") || render_empty(__("No quick actions are available for this role preview."))}
				</div>
			</section>

			<section class="arl-kpi-grid">
				${as_array(KPI_GROUPS).filter((group) => kpis.includes(group.key))
					.map(render_kpi_group)
					.join("")}
			</section>

			<section class="arl-module-grid">
				${as_array(MODULE_TILES).filter((tile) => sections.includes(tile.key))
					.map(render_module_tile)
					.join("")}
			</section>

			<section class="arl-lower-grid ${can_preview_roles ? "" : "single"}">
				${render_activity(profile)}
				${can_preview_roles ? render_role_examples() : ""}
			</section>
		`;
	}

	function render_action(action) {
		return `
			<button class="arl-action" type="button" data-route="${escape_attr(action.route)}">
				<span class="arl-action-icon">${icon(action.icon)}</span>
				<span>${escape_html(action.label)}</span>
			</button>
		`;
	}

	function render_kpi_group(group) {
		const items = as_array(group.items);
		return `
			<div class="arl-panel arl-kpi-group">
				<div class="arl-section-head compact">
					<h3>${escape_html(group.label)}</h3>
				</div>
				<div class="arl-kpis">
					${items.map((item) => `
						<div class="arl-kpi">
							<div class="arl-kpi-label">${escape_html(item.label)}</div>
							<div class="arl-kpi-value">${escape_html(item.value)}</div>
							<div class="arl-kpi-note ${item.tone || ""}">${escape_html(item.note)}</div>
						</div>
					`).join("")}
				</div>
			</div>
		`;
	}

	function render_module_tile(tile) {
		return `
			<button class="arl-module" type="button" data-route="${escape_attr(tile.route)}">
				<span class="arl-module-icon">${icon(tile.icon)}</span>
				<span class="arl-module-copy">
					<strong>${escape_html(tile.label)}</strong>
					<small>${escape_html(tile.description)}</small>
				</span>
				<span class="arl-module-open">${__("Open")}</span>
			</button>
		`;
	}

	function render_activity(profile) {
		const activity = as_array(profile.activity);
		const rows = as_array(SAMPLE_ACTIVITY).filter((row) => activity.includes(row.type));
		return `
			<div class="arl-panel">
				<div class="arl-section-head">
					<div>
						<h3>${__("Recent Work")}</h3>
						<p>${__("Fictional AL RANA sample activity for design preview")}</p>
					</div>
				</div>
				<div class="arl-activity-list">
					${rows.map((row) => `
						<button class="arl-activity" type="button" data-route="${escape_attr(row.route)}">
							<span class="arl-activity-id">${escape_html(row.id)}</span>
							<span class="arl-activity-main">
								<strong>${escape_html(row.title)}</strong>
								<small>${escape_html(row.meta)}</small>
							</span>
							<span class="arl-chip ${escape_attr(row.tone)}">${escape_html(row.status)}</span>
						</button>
					`).join("") || render_empty(__("No sample activity for this role preview."))}
				</div>
			</div>
		`;
	}

	function render_role_examples() {
		const preview_profiles = Object.entries(ROLE_PROFILES).filter((entry) => entry[1] && entry[1].preview);
		return `
			<div class="arl-panel">
				<div class="arl-section-head">
					<div>
						<h3>${__("Role Visibility Examples")}</h3>
						<p>${__("Sidebar sections shown for key office roles")}</p>
					</div>
				</div>
				<div class="arl-role-examples">
					${preview_profiles
						.map(([key, profile]) => `
							<button class="arl-role-card ${key === state.profile ? "active" : ""}" type="button" data-profile="${escape_attr(key)}">
								<strong>${escape_html(profile.label)}</strong>
								<span>${as_array(profile.sections).map(section_label).join(" · ")}</span>
							</button>
						`).join("")}
				</div>
			</div>
		`;
	}

	function render_empty(text) {
		return `<div class="arl-empty">${escape_html(text)}</div>`;
	}

	function bind_events() {
		$root.find("[data-route]").on("click", function () {
			const route = $(this).attr("data-route");
			if (route) {
				open_route(route);
			}
		});
		$root.find("[data-profile]").on("click", function () {
			if (!can_preview_roles) {
				return;
			}
			state.profile = ROLE_PROFILES[$(this).attr("data-profile")] ? $(this).attr("data-profile") : get_default_profile();
			safe_render();
		});
		$root.find('[data-action="toggle-sidebar"]').on("click", function () {
			state.collapsed = !state.collapsed;
			safe_render();
		});
	}
};

const ROLE_PROFILES = {
	transport_manager: {
		label: __("Transport Manager"),
		short: __("Manager"),
		preview: true,
		sections: ["dashboard", "operations", "fleet", "expenses", "finance", "reports", "administration"],
		actions: ["new_trip", "new_expense_claim", "new_employee_advance", "new_purchase_invoice"],
		kpis: ["operations", "expenses", "finance"],
		activity: ["trip", "expense", "invoice"],
	},
	accounts: {
		label: __("Accounts User"),
		short: __("Accounts"),
		preview: true,
		sections: ["dashboard", "expenses", "finance", "reports"],
		actions: ["new_purchase_invoice", "new_payment_entry"],
		kpis: ["expenses", "finance"],
		activity: ["expense", "invoice", "payment"],
	},
	hr_manager: {
		label: __("HR Manager"),
		short: __("HR"),
		preview: true,
		sections: ["dashboard", "expenses", "hr", "reports"],
		actions: ["new_expense_claim", "new_employee_advance"],
		kpis: ["expenses"],
		activity: ["expense", "advance"],
	},
	dispatcher: {
		label: __("Dispatcher"),
		short: __("Dispatcher"),
		preview: true,
		sections: ["dashboard", "operations", "fleet", "reports"],
		actions: ["new_trip"],
		kpis: ["operations"],
		activity: ["trip", "document"],
	},
	trip_entry: {
		label: __("TMS Trip Data Entry"),
		short: __("Trips"),
		preview: false,
		sections: ["dashboard", "operations", "fleet", "reports"],
		actions: ["new_trip"],
		kpis: ["operations"],
		activity: ["trip", "document"],
	},
	minimal: {
		label: __("AL RANA User"),
		short: __("User"),
		preview: false,
		sections: ["dashboard"],
		actions: [],
		kpis: [],
		activity: [],
	},
	admin: {
		label: __("Transport Admin"),
		short: __("Admin"),
		preview: false,
		sections: ["dashboard", "operations", "fleet", "expenses", "finance", "hr", "reports", "administration"],
		actions: ["new_trip", "new_expense_claim", "new_employee_advance", "new_purchase_invoice", "new_payment_entry"],
		kpis: ["operations", "expenses", "finance"],
		activity: ["trip", "expense", "invoice", "payment", "advance", "document"],
	},
};

const ROLE_TO_PROFILE = {
	"Transport Admin": "admin",
	"System Manager": "admin",
	"Transport Manager": "transport_manager",
	"Accounts Manager": "accounts",
	"Accounts User": "accounts",
	"HR Manager": "hr_manager",
	"HR User": "hr_manager",
	"Expense Approver": "hr_manager",
	"TMS + Expense Data Entry": "transport_manager",
	"TMS Trip Data Entry": "trip_entry",
};

const NAV_GROUPS = [
	{ key: "dashboard", label: __("Dashboard"), icon: "dashboard", route: "/app/al-rana-home" },
	{
		key: "operations",
		label: __("Operations"),
		icon: "route",
		items: [
			{ label: __("Trip Operations"), icon: "activity", route: "/app/tms-trip-operations" },
			{ label: __("Jobs"), icon: "briefcase", route: "/app/transport-job" },
			{ label: __("Trips"), icon: "truck", route: "/app/transport-trip" },
			{ label: __("Transport Sales Orders"), icon: "clipboard", route: "/app/transport-sales-order", profiles: ["transport_manager", "admin"] },
			{ label: __("Dispatcher Console"), icon: "monitor", route: "/app/tms-trip-operations" },
			{ label: __("Trip Documents"), icon: "file", route: "/app/transport-trip-document" },
		],
	},
	{
		key: "fleet",
		label: __("Fleet"),
		icon: "truck",
		items: [
			{ label: __("Trucks"), icon: "truck", route: "/app/truck" },
			{ label: __("Drivers"), icon: "user", route: "/app/truck-driver" },
			{ label: __("Hired Vehicles"), icon: "car", route: "/app/hired-vehicle" },
		],
	},
	{
		key: "expenses",
		label: __("Expenses"),
		icon: "receipt",
		items: [
			{ label: __("Expense Claims"), icon: "receipt", route: "/app/expense-claim" },
			{ label: __("Driver Advances"), icon: "wallet", route: "/app/employee-advance" },
			{ label: __("Expense Reports"), icon: "chart", route: "/app/query-report/Unpaid Expense Claim" },
		],
	},
	{
		key: "finance",
		label: __("Finance"),
		icon: "accounting",
		items: [
			{ label: __("Sales Invoices"), icon: "file", route: "/app/sales-invoice" },
			{ label: __("Purchase Invoices"), icon: "file", route: "/app/purchase-invoice" },
			{ label: __("Payment Entries"), icon: "payment", route: "/app/payment-entry" },
			{ label: __("General Ledger"), icon: "ledger", route: "/app/query-report/General Ledger" },
			{ label: __("Accounts Receivable"), icon: "arrow-down", route: "/app/query-report/Accounts Receivable" },
			{ label: __("Accounts Payable"), icon: "arrow-up", route: "/app/query-report/Accounts Payable" },
		],
	},
	{
		key: "hr",
		label: __("HR"),
		icon: "users",
		items: [
			{ label: __("Employees"), icon: "user", route: "/app/employee" },
			{ label: __("Expense Approvals"), icon: "check", route: "/app/expense-claim" },
		],
	},
	{
		key: "reports",
		label: __("Reports"),
		icon: "chart",
		items: [
			{ label: __("Operations Reports"), icon: "chart", route: "/app/query-report/Sales Order Analysis" },
			{ label: __("Expense Reports"), icon: "chart", route: "/app/query-report/Employee Advance Summary" },
			{ label: __("Finance Reports"), icon: "chart", route: "/app/query-report/General Ledger" },
		],
	},
	{
		key: "administration",
		label: __("Administration"),
		icon: "settings",
		items: [
			{ label: __("Charge Rules"), icon: "settings", route: "/app/transport-charge-rule" },
			{ label: __("Transport Rates"), icon: "money", route: "/app/transport-rate" },
			{ label: __("Locations"), icon: "location", route: "/app/transport-location" },
			{ label: __("Truck Types"), icon: "truck", route: "/app/truck-type" },
			{ label: __("Materials"), icon: "stock", route: "/app/cargo-types" },
			{ label: __("Data Import"), icon: "upload", route: "/app/tms-data-import" },
			{ label: __("TMS Settings"), icon: "settings", route: "/app/tms-billing-settings" },
		],
	},
];

const QUICK_ACTIONS = [
	{ key: "new_trip", label: __("New Trip"), icon: "plus", route: "new:Transport Trip" },
	{ key: "new_expense_claim", label: __("New Expense Claim"), icon: "plus", route: "new:Expense Claim" },
	{ key: "new_employee_advance", label: __("New Employee Advance"), icon: "plus", route: "new:Employee Advance" },
	{ key: "new_purchase_invoice", label: __("New Purchase Invoice"), icon: "plus", route: "new:Purchase Invoice" },
	{ key: "new_payment_entry", label: __("New Payment Entry"), icon: "plus", route: "new:Payment Entry" },
];

const KPI_GROUPS = [
	{
		key: "operations",
		label: __("Operations"),
		items: [
			{ label: __("Active Trips"), value: "42", note: __("Demo: 17 in transit"), tone: "blue" },
			{ label: __("Awaiting Assignment"), value: "8", note: __("Demo: needs dispatcher action"), tone: "amber" },
			{ label: __("In Transit"), value: "17", note: __("Demo: live route work"), tone: "green" },
			{ label: __("Documents Pending"), value: "6", note: __("Demo: POD review queue"), tone: "amber" },
		],
	},
	{
		key: "expenses",
		label: __("Expenses"),
		items: [
			{ label: __("Claims Pending Approval"), value: "9", note: __("Demo: AED 3,240"), tone: "amber" },
			{ label: __("Driver Advances Outstanding"), value: "AED 12,500", note: __("Demo: 25 drivers"), tone: "blue" },
		],
	},
	{
		key: "finance",
		label: __("Finance"),
		items: [
			{ label: __("Unpaid Sales Invoices"), value: "AED 184,000", note: __("Demo: 14 invoices"), tone: "blue" },
			{ label: __("Supplier Payables"), value: "AED 96,400", note: __("Demo: 11 bills"), tone: "amber" },
		],
	},
];

const MODULE_TILES = [
	{ key: "operations", label: __("Operations"), description: __("Jobs, trips and dispatch activity"), icon: "route", route: "/app/tms-trip-operations" },
	{ key: "expenses", label: __("Expenses"), description: __("Expense claims and driver advances"), icon: "receipt", route: "/app/expense-claim" },
	{ key: "finance", label: __("Finance"), description: __("Invoices, payments and ledgers"), icon: "accounting", route: "/app/sales-invoice" },
	{ key: "hr", label: __("HR"), description: __("Employees and approvals"), icon: "users", route: "/app/employee" },
	{ key: "administration", label: __("Administration"), description: __("Rates, charge rules and masters"), icon: "settings", route: "/app/transport-charge-rule" },
];

const SAMPLE_ACTIVITY = [
	{ type: "trip", id: "TTRIP-2026-0142", title: "FUJ to AJMAN aggregate delivery", meta: "Driver: Ahmed Khan · Truck: 22884-DXB", status: "In Transit", tone: "blue", route: "/app/transport-trip" },
	{ type: "trip", id: "TTRIP-2026-0145", title: "National Quarries loading pending", meta: "Dispatcher queue · 82.5 TON", status: "Awaiting Assignment", tone: "amber", route: "/app/tms-trip-operations" },
	{ type: "document", id: "TDOC-2026-0031", title: "POD requires verification", meta: "Trip TTRIP-2026-0138 · Uploaded 09:20", status: "Review", tone: "amber", route: "/app/transport-trip-document" },
	{ type: "expense", id: "HR-EXP-2026-0024", title: "Fuel claim from UMAIR", meta: "AED 210 · Trip TTRIP-2026-0135", status: "Pending", tone: "amber", route: "/app/expense-claim" },
	{ type: "advance", id: "HR-EAD-2026-0012", title: "Driver standing float", meta: "AED 500 · AMRINDER SINGH", status: "Paid", tone: "green", route: "/app/employee-advance" },
	{ type: "invoice", id: "ACC-SINV-2026-0087", title: "Transport invoice batch", meta: "AED 18,450 · Tech Remix LLC", status: "Draft", tone: "blue", route: "/app/sales-invoice" },
	{ type: "payment", id: "ACC-PAY-2026-0041", title: "Supplier payment prepared", meta: "AED 7,800 · Cash - ARL", status: "Draft", tone: "blue", route: "/app/payment-entry" },
];

function get_default_profile() {
	return get_effective_navigation_roles()[0] || "minimal";
}

function get_effective_navigation_roles() {
	const roles = as_array(frappe.user_roles);
	const profiles = roles
		.map((role) => ROLE_TO_PROFILE[role])
		.filter(Boolean);
	return [...new Set(profiles)].sort((left, right) => profile_priority(left) - profile_priority(right));
}

function profile_priority(profile) {
	const priority = {
		admin: 10,
		transport_manager: 20,
		accounts: 30,
		hr_manager: 40,
		trip_entry: 50,
		minimal: 99,
	};
	return priority[profile] || 90;
}

function get_profile(profile_key) {
	const profile = ROLE_PROFILES[profile_key] || ROLE_PROFILES[get_default_profile()] || ROLE_PROFILES.minimal;
	return {
		...profile,
		sections: as_array(profile.sections),
		actions: as_array(profile.actions),
		kpis: as_array(profile.kpis),
		activity: as_array(profile.activity),
	};
}

function as_array(value) {
	return Array.isArray(value) ? value : [];
}

function section_label(key) {
	const group = NAV_GROUPS.find((item) => item.key === key);
	return group ? escape_html(group.label) : "";
}

function open_route(route) {
	if (!route) return;
	if (route.startsWith("new:")) {
		frappe.new_doc(route.slice(4));
		return;
	}
	const parts = route.replace(/^\/app\//, "").split("/").filter(Boolean);
	frappe.set_route(...parts);
}

function icon(name) {
	try {
		return frappe.utils.icon(name, "sm") || "";
	} catch (error) {
		console.warn(`AL RANA Home icon not available: ${name}`, error);
		return "";
	}
}

function can_preview_al_rana_roles() {
	const roles = new Set(frappe.user_roles || []);
	return roles.has("System Manager") || roles.has("Transport Admin");
}

function get_initials(value) {
	return String(value || "AR")
		.split(/\s+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part.charAt(0).toUpperCase())
		.join("") || "AR";
}

function escape_html(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
}

function escape_attr(value) {
	return escape_html(value).replace(/"/g, "&quot;");
}

function ensure_al_rana_home_styles() {
	if (document.getElementById("al-rana-home-styles")) {
		return;
	}

	$(`
		<style id="al-rana-home-styles">
			.arl-shell {
				--arl-navy: #0b1f33;
				--arl-slate: #334155;
				--arl-muted: #64748b;
				--arl-line: #dbe3ec;
				--arl-soft: #f6f8fb;
				--arl-teal: #0f8f8c;
				--arl-blue: #2563eb;
				--arl-green: #027a48;
				--arl-amber: #b76e00;
				background: #f4f6f9;
				color: #172033;
				display: grid;
				grid-template-columns: 236px minmax(0, 1fr);
				min-height: calc(100vh - 108px);
			}
			.arl-shell.is-collapsed {
				grid-template-columns: 72px minmax(0, 1fr);
			}
			.arl-sidebar {
				background: #ffffff;
				border-right: 1px solid var(--arl-line);
				display: flex;
				flex-direction: column;
				min-height: calc(100vh - 108px);
				padding: 14px 12px;
				position: sticky;
				top: 0;
			}
			.arl-brand {
				align-items: center;
				display: flex;
				gap: 10px;
				min-height: 48px;
				padding: 2px 4px 14px;
			}
			.arl-brand-mark {
				align-items: center;
				background: linear-gradient(135deg, var(--arl-teal), var(--arl-navy));
				border-radius: 8px;
				color: #fff;
				display: inline-flex;
				flex: 0 0 38px;
				font-size: 13px;
				font-weight: 800;
				height: 38px;
				justify-content: center;
				letter-spacing: 0;
				width: 38px;
			}
			.arl-brand-name,
			.arl-user-name {
				color: var(--arl-navy);
				font-size: 13px;
				font-weight: 800;
				line-height: 1.2;
			}
			.arl-brand-subtitle,
			.arl-user-role,
			.arl-breadcrumb,
			.arl-section-head p,
			.arl-module small,
			.arl-activity small {
				color: var(--arl-muted);
				font-size: 12px;
				line-height: 1.4;
			}
			.arl-nav {
				flex: 1;
				overflow-y: auto;
				padding-right: 2px;
			}
			.arl-nav-group {
				margin-bottom: 8px;
			}
			.arl-nav-parent,
			.arl-nav-item,
			.arl-collapse,
			.arl-module,
			.arl-activity,
			.arl-action,
			.arl-role-card {
				background: transparent;
				border: 0;
				text-align: left;
			}
			.arl-nav-parent,
			.arl-nav-item,
			.arl-collapse {
				align-items: center;
				border-radius: 7px;
				color: var(--arl-slate);
				display: flex;
				gap: 9px;
				min-height: 34px;
				padding: 7px 8px;
				width: 100%;
			}
			.arl-nav-parent {
				color: var(--arl-navy);
				font-size: 11px;
				font-weight: 800;
				letter-spacing: 0;
				text-transform: uppercase;
			}
			.arl-nav-item {
				font-size: 13px;
				font-weight: 600;
				margin-top: 2px;
				padding-left: 28px;
			}
			.arl-nav-item.is-root {
				background: #eaf6f5;
				color: #05615f;
				font-weight: 800;
				margin-bottom: 10px;
				padding-left: 8px;
			}
			.arl-nav-parent:hover,
			.arl-nav-item:hover,
			.arl-action:hover,
			.arl-module:hover,
			.arl-activity:hover,
			.arl-role-card:hover {
				background: var(--arl-soft);
			}
			.arl-nav-icon {
				align-items: center;
				display: inline-flex;
				flex: 0 0 16px;
				justify-content: center;
			}
			.arl-sidebar-footer {
				border-top: 1px solid var(--arl-line);
				padding-top: 10px;
			}
			.arl-collapse {
				font-size: 12px;
				font-weight: 700;
				margin-bottom: 8px;
			}
			.arl-user {
				align-items: center;
				display: flex;
				gap: 9px;
				min-height: 42px;
				padding: 4px;
			}
			.arl-avatar {
				align-items: center;
				background: #eef2f7;
				border: 1px solid var(--arl-line);
				border-radius: 50%;
				color: var(--arl-navy);
				display: inline-flex;
				flex: 0 0 34px;
				font-size: 12px;
				font-weight: 800;
				height: 34px;
				justify-content: center;
				width: 34px;
			}
			.is-collapsed .arl-brand-copy,
			.is-collapsed .arl-nav-label,
			.is-collapsed .arl-user-copy,
			.is-collapsed .arl-collapse span,
			.is-collapsed .arl-nav-children {
				display: none;
			}
			.is-collapsed .arl-sidebar {
				padding-left: 10px;
				padding-right: 10px;
			}
			.is-collapsed .arl-nav-parent,
			.is-collapsed .arl-nav-item,
			.is-collapsed .arl-collapse {
				justify-content: center;
				padding-left: 8px;
				padding-right: 8px;
			}
			.arl-main {
				min-width: 0;
				padding: 18px;
			}
			.arl-topbar {
				align-items: center;
				display: flex;
				gap: 16px;
				justify-content: space-between;
				margin-bottom: 16px;
			}
			.arl-topbar h1 {
				font-size: 25px;
				font-weight: 800;
				line-height: 1.2;
				margin: 2px 0 0;
			}
			.arl-topbar-actions {
				align-items: center;
				display: flex;
				gap: 10px;
				min-width: 0;
			}
			.arl-search {
				align-items: center;
				background: #fff;
				border: 1px solid var(--arl-line);
				border-radius: 8px;
				color: var(--arl-muted);
				display: flex;
				gap: 8px;
				min-width: 250px;
				padding: 9px 11px;
			}
			.arl-role-switcher {
				background: #fff;
				border: 1px solid var(--arl-line);
				border-radius: 8px;
				display: flex;
				gap: 3px;
				padding: 3px;
			}
			.arl-role-switcher span {
				align-items: center;
				color: var(--arl-muted);
				display: inline-flex;
				font-size: 11px;
				font-weight: 800;
				padding: 0 7px;
				text-transform: uppercase;
			}
			.arl-role-switcher button {
				background: transparent;
				border: 0;
				border-radius: 6px;
				color: var(--arl-muted);
				font-size: 12px;
				font-weight: 700;
				padding: 7px 9px;
			}
			.arl-role-switcher button.active {
				background: var(--arl-navy);
				color: #fff;
			}
			.arl-hero,
			.arl-panel,
			.arl-module,
			.arl-action {
				background: #fff;
				border: 1px solid var(--arl-line);
				border-radius: 8px;
			}
			.arl-hero {
				align-items: center;
				display: flex;
				justify-content: space-between;
				margin-bottom: 14px;
				padding: 18px;
			}
			.arl-demo-label {
				color: var(--arl-teal);
				font-size: 11px;
				font-weight: 800;
				letter-spacing: 0;
				margin-bottom: 5px;
				text-transform: uppercase;
			}
			.arl-hero h2 {
				font-size: 25px;
				font-weight: 800;
				margin: 0 0 5px;
			}
			.arl-hero p {
				color: var(--arl-muted);
				margin: 0;
			}
			.arl-hero-status {
				align-items: center;
				color: var(--arl-muted);
				display: flex;
				font-size: 13px;
				font-weight: 700;
				gap: 8px;
			}
			.arl-status-dot {
				background: var(--arl-green);
				border-radius: 50%;
				height: 9px;
				width: 9px;
			}
			.arl-panel {
				margin-bottom: 14px;
				padding: 15px;
			}
			.arl-section-head {
				align-items: center;
				display: flex;
				justify-content: space-between;
				margin-bottom: 12px;
			}
			.arl-section-head h3 {
				font-size: 15px;
				font-weight: 800;
				margin: 0;
			}
			.arl-section-head p {
				margin: 3px 0 0;
			}
			.arl-section-head.compact {
				margin-bottom: 10px;
			}
			.arl-quick-actions,
			.arl-module-grid,
			.arl-role-examples {
				display: grid;
				gap: 10px;
			}
			.arl-quick-actions {
				grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
			}
			.arl-action {
				align-items: center;
				display: flex;
				gap: 10px;
				min-height: 48px;
				padding: 10px 12px;
			}
			.arl-action-icon,
			.arl-module-icon {
				align-items: center;
				background: #eef7f7;
				border-radius: 7px;
				color: var(--arl-teal);
				display: inline-flex;
				flex: 0 0 30px;
				height: 30px;
				justify-content: center;
				width: 30px;
			}
			.arl-kpi-grid {
				display: grid;
				gap: 14px;
				grid-template-columns: repeat(3, minmax(240px, 1fr));
			}
			.arl-kpis {
				display: grid;
				gap: 8px;
				grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
			}
			.arl-kpi {
				background: var(--arl-soft);
				border: 1px solid #e7edf4;
				border-radius: 8px;
				padding: 11px;
			}
			.arl-kpi-label {
				color: var(--arl-muted);
				font-size: 11px;
				font-weight: 800;
				text-transform: uppercase;
			}
			.arl-kpi-value {
				font-size: 23px;
				font-weight: 850;
				line-height: 1.1;
				margin: 7px 0 5px;
			}
			.arl-kpi-note {
				color: var(--arl-muted);
				font-size: 12px;
			}
			.arl-kpi-note.green { color: var(--arl-green); }
			.arl-kpi-note.amber { color: var(--arl-amber); }
			.arl-kpi-note.blue { color: var(--arl-blue); }
			.arl-module-grid {
				grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
				margin-bottom: 14px;
			}
			.arl-module {
				align-items: center;
				display: flex;
				gap: 11px;
				min-height: 80px;
				padding: 14px;
				width: 100%;
			}
			.arl-module-copy {
				display: grid;
				flex: 1;
				gap: 3px;
				min-width: 0;
			}
			.arl-module-copy strong {
				color: var(--arl-navy);
				font-size: 14px;
			}
			.arl-module-open {
				color: var(--arl-teal);
				font-size: 12px;
				font-weight: 800;
			}
			.arl-lower-grid {
				display: grid;
				gap: 14px;
				grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.65fr);
			}
			.arl-lower-grid.single {
				grid-template-columns: 1fr;
			}
			.arl-activity-list {
				display: grid;
				gap: 7px;
			}
			.arl-activity {
				align-items: center;
				border-radius: 8px;
				display: grid;
				gap: 10px;
				grid-template-columns: 132px minmax(0, 1fr) auto;
				padding: 9px 10px;
				width: 100%;
			}
			.arl-activity-id {
				color: var(--arl-blue);
				font-size: 12px;
				font-weight: 800;
			}
			.arl-activity-main {
				display: grid;
				gap: 2px;
				min-width: 0;
			}
			.arl-activity-main strong,
			.arl-activity-main small {
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			}
			.arl-chip {
				border-radius: 999px;
				font-size: 11px;
				font-weight: 800;
				padding: 5px 8px;
			}
			.arl-chip.green { background: #ecfdf3; color: var(--arl-green); }
			.arl-chip.amber { background: #fff7e6; color: var(--arl-amber); }
			.arl-chip.blue { background: #eff6ff; color: var(--arl-blue); }
			.arl-role-examples {
				grid-template-columns: 1fr;
			}
			.arl-role-card {
				border: 1px solid var(--arl-line);
				border-radius: 8px;
				display: grid;
				gap: 4px;
				padding: 11px;
				width: 100%;
			}
			.arl-role-card.active {
				background: #eef7f7;
				border-color: #9bd2d0;
			}
			.arl-role-card span {
				color: var(--arl-muted);
				font-size: 12px;
				line-height: 1.4;
			}
			.arl-empty {
				border: 1px dashed var(--arl-line);
				border-radius: 8px;
				color: var(--arl-muted);
				padding: 12px;
			}
			.arl-error-main {
				display: flex;
				min-height: 360px;
			}
			.arl-error-panel {
				margin: auto;
				max-width: 520px;
				width: 100%;
			}
			.arl-error-panel h2 {
				color: var(--arl-navy);
				font-size: 22px;
				font-weight: 800;
				margin: 0 0 8px;
			}
			.arl-error-panel p {
				color: var(--arl-muted);
				margin: 0 0 16px;
			}
			.arl-nav-parent:focus-visible,
			.arl-nav-item:focus-visible,
			.arl-action:focus-visible,
			.arl-module:focus-visible,
			.arl-activity:focus-visible,
			.arl-role-card:focus-visible,
			.arl-collapse:focus-visible,
			.arl-role-switcher button:focus-visible {
				box-shadow: 0 0 0 3px rgba(15, 143, 140, 0.22);
				outline: 2px solid transparent;
			}
			@media (max-width: 1180px) {
				.arl-shell {
					grid-template-columns: 72px minmax(0, 1fr);
				}
				.arl-shell .arl-brand-copy,
				.arl-shell .arl-nav-label,
				.arl-shell .arl-user-copy,
				.arl-shell .arl-collapse span,
				.arl-shell .arl-nav-children {
					display: none;
				}
				.arl-shell .arl-nav-parent,
				.arl-shell .arl-nav-item,
				.arl-shell .arl-collapse {
					justify-content: center;
					padding-left: 8px;
					padding-right: 8px;
				}
				.arl-kpi-grid,
				.arl-lower-grid {
					grid-template-columns: 1fr;
				}
			}
			@media (max-width: 760px) {
				.arl-shell {
					display: block;
				}
				.arl-sidebar {
					min-height: 0;
					position: relative;
				}
				.arl-main {
					padding: 14px;
				}
				.arl-topbar,
				.arl-hero {
					align-items: flex-start;
					flex-direction: column;
				}
				.arl-topbar-actions {
					align-items: stretch;
					flex-direction: column;
					width: 100%;
				}
				.arl-search {
					min-width: 0;
					width: 100%;
				}
				.arl-role-switcher {
					overflow-x: auto;
				}
				.arl-activity {
					grid-template-columns: 1fr;
				}
			}
		</style>
	`).appendTo("head");
}
