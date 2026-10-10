// AL RANA Dispatch - dispatcher console page bootstrap.
//
// Frappe loads this file as the script of the `dispatch-console` Page document
// (al_rana_dispatch/page/dispatch_console/dispatch_console.js).  It builds the
// console shell once and then re-renders the active section whenever the Desk
// route changes (/app/dispatch-console/<section>).
//
// The five section views live in public/js/dispatch_portal/* and are attached to
// frappe.pages through the `page_js` hook, so they are evaluated before
// on_page_load runs.

frappe.provide("dispatch_portal");

frappe.provide("dispatch_portal.views");

dispatch_portal.Console = {
	page_name: "dispatch-console",
	title: "AL RANA Dispatch",

	sections: [
		{
			key: "dashboard",
			label: __("Dashboard"),
			subtitle: __("Live fleet and trip picture for the shift"),
		},
		{key: "trips", label: __("Trips"), subtitle: __("Plan, assign and move trips")},
		{key: "trip-map", label: __("Trip Map"), subtitle: __("Trip routes and loading stops")},
		{
			key: "verification",
			label: __("Verification"),
			subtitle: __("Review trip documents and AI extraction"),
		},
		{key: "reports", label: __("Reports"), subtitle: __("Operational rollups and exports")},
	],

	on_page_load(wrapper) {
		this.wrapper = wrapper;
		this.boot = null;
		this.current_section = null;
		this.render_shell();
		this.load_boot();
	},

	on_page_show() {
		this.render_section(this.get_section_from_route());
	},

	get_section_from_route() {
		const route = frappe.get_route() || [];
		const section = route[1];
		return section && this.sections.some((row) => row.key === section) ? section : "dashboard";
	},

	get sections_for_user() {
		const allowed = (this.boot && this.boot.sections) || this.sections.map((row) => row.key);
		return this.sections.filter((row) => allowed.includes(row.key));
	},

	get section_meta() {
		const key = this.current_section || "dashboard";
		return this.sections.find((row) => row.key === key) || this.sections[0];
	},

	render_shell() {
		const $shell = $(
			`<div class="al-dispatch">
				<aside class="al-dispatch-rail">
					<div class="al-dispatch-brand">
						<span class="al-dispatch-brand-mark">${dispatch_portal.Console.markup()}</span>
						<span class="al-dispatch-brand-text">
							<span class="al-dispatch-brand-name">AL RANA</span>
							<span class="al-dispatch-brand-sub">${__("Dispatch")}</span>
						</span>
					</div>
					<nav class="al-dispatch-nav"></nav>
					<div class="al-dispatch-rail-footer"></div>
				</aside>
				<div class="al-dispatch-content">
					<header class="al-dispatch-topbar">
						<div class="al-dispatch-heading">
							<h4 class="al-dispatch-title"></h4>
							<p class="al-dispatch-subtitle"></p>
						</div>
						<div class="al-dispatch-topbar-actions"></div>
					</header>
					<div class="al-dispatch-section" data-section></div>
				</div>
			</div>`
		);

		$(this.wrapper).empty().append($shell);
		this.$shell = $shell;
		this.$nav = $shell.find(".al-dispatch-nav");
		this.$title = $shell.find(".al-dispatch-title");
		this.$subtitle = $shell.find(".al-dispatch-subtitle");
		this.$actions = $shell.find(".al-dispatch-topbar-actions");
		this.$section = $shell.find("[data-section]");
		this.render_nav();
	},

	markup() {
		return `<svg viewBox="0 0 64 64" role="img" aria-label="AL RANA Dispatch">
			<rect width="64" height="64" rx="14" fill="#0B2545"></rect>
			<path d="M14 37h4V24c0-2.2 1.8-4 4-4h19c2.2 0 4 1.8 4 4v5h5.1c1.2 0 2.3.6 3 1.6l4.1 6.1c.5.7.8 1.6.8 2.5V45h-5.1a7 7 0 0 1-13.8 0H28.9a7 7 0 0 1-13.8 0H14v-8Zm8-12v12h18V25H22Zm23 9v3h8.1l-2-3H45Z" fill="#FFFFFF"></path>
			<circle cx="22" cy="45" r="3" fill="#38BDF8"></circle>
			<circle cx="46" cy="45" r="3" fill="#38BDF8"></circle>
		</svg>`;
	},

	render_nav() {
		const me = this;
		this.$nav.empty();
		this.sections_for_user.forEach((row) => {
			const $item = $(
				`<a class="al-dispatch-nav-item" href="/app/dispatch-console/${row.key}" data-section-link="${row.key}">
					<span class="al-dispatch-nav-icon">${frappe.utils.icon(me.nav_icon(row.key))}</span>
					<span class="al-dispatch-nav-label">${row.label}</span>
				</a>`
			);
			if ((this.current_section || "dashboard") === row.key) {
				$item.addClass("active");
			}
			this.$nav.append($item);
		});

		if (this.boot && this.boot.permissions) {
			const permissions = this.boot.permissions;
			this.$shell.find(".al-dispatch-rail-footer").html(
				`<div class="al-dispatch-user">
					<span class="al-dispatch-user-name">${frappe.utils.escape_html(
						permissions.full_name || permissions.user
					)}</span>
					<span class="al-dispatch-user-badge">${this.role_badge(permissions)}</span>
				</div>`
			);
		}
	},

	role_badge(permissions) {
		if (permissions.is_verifier) {
			return __("Dispatcher + Verifier");
		}
		return __("Dispatcher");
	},

	nav_icon(key) {
		return {
			dashboard: "layout-dashboard",
			trips: "list",
			"trip-map": "map",
			verification: "clipboard-check",
			reports: "chart-column",
		}[key] || "small-forward";
	},

	load_boot() {
		const me = this;
		frappe
			.call({
				method: "dispatch_portal.api.permissions.get_console_boot",
				freeze: false,
			})
			.then((r) => {
				me.boot = r.message || {};
				me.render_nav();
				me.render_section(me.get_section_from_route());
			})
			.catch(() => {
				frappe.show_not_permitted(me.page_name);
			});
	},

	render_section(section) {
		if (!this.boot) {
			return;
		}
		if (!this.sections_for_user.some((row) => row.key === section)) {
			section = "dashboard";
		}

		const view = dispatch_portal.views[section];
		if (!view) {
			this.$section.html(
				`<div class="al-dispatch-empty">${__("Section is not available.")}</div>`
			);
			return;
		}

		this.current_section = section;
		this.$title.text(this.section_meta.label);
		this.$subtitle.text(this.section_meta.subtitle);
		this.render_nav();
		this.$section.empty();
		this.$actions.empty();
		frappe.breadcrumbs.update();

		const context = {
			container: this.$section,
			actions: this.$actions,
			console: this,
			permissions: this.boot.permissions || {},
			boot: this.boot,
		};

		if (typeof view.render === "function") {
			view.render(context);
		}
	},

	refresh() {
		this.render_section(this.current_section || "dashboard");
	},

	set_actions(buttons) {
		const me = this;
		this.$actions.empty();
		(buttons || []).forEach((button) => {
			const $button = $(
				`<button class="btn btn-sm ${button.primary ? "btn-primary" : "btn-default"} al-dispatch-action">
					${frappe.utils.icon(button.icon || "rotate-cw")}
					<span>${button.label}</span>
				</button>`
			);
			$button.on("click", () => button.onClick(me.$section));
			me.$actions.append($button);
		});
	},

	show_loading(message) {
		this.$section.html(
			`<div class="al-dispatch-loading">
				<span class="al-dispatch-spinner"></span>
				<span>${message || __("Loading")}</span>
			</div>`
		);
	},

	show_error(error) {
		const message =
			(error && error._server_messages && frappe.parse_json(error._server_messages)) ||
			(error && error.message) ||
			__("Something went wrong.");
		this.$section.html(
			`<div class="al-dispatch-error">
				<strong>${__("Unable to load this section")}</strong>
				<p>${message}</p>
			</div>`
		);
	},

	navigate(section, extra) {
		if (extra) {
			frappe.set_route("dispatch-console", section, extra);
			return;
		}
		frappe.set_route("dispatch-console", section);
	},

	call(options) {
		return frappe.call(
			Object.assign({freeze: false, error_handler: (error) => this.show_error(error)}, options)
		);
	},
};

frappe.pages["dispatch-console"].on_page_load = function (wrapper) {
	dispatch_portal.Console.on_page_load(wrapper);
};

frappe.pages["dispatch-console"].on_page_show = function () {
	dispatch_portal.Console.on_page_show();
};
