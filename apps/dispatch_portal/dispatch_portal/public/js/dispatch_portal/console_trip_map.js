// Trip Map section of the AL RANA Dispatch console.
// Coordinates come from the Transport Location master data owned by the TMS.

frappe.provide("dispatch_portal.views");

dispatch_portal.views["trip-map"] = {
	render(context) {
		this.container = context.container;
		this.console = context.console;
		this.permissions = context.permissions || {};
		this.map = null;
		this.layers = [];

		context.console.set_actions([
			{label: __("Refresh"), icon: "rotate-cw", onClick: () => this.load()},
			{
				label: __("Trips"),
				icon: "list",
				onClick: () => this.console.navigate("trips"),
			},
		]);

		this.render_shell();
		this.load();
	},

	render_shell() {
		const utils = dispatch_portal.utils;
		const groups = [
			{value: "", label: __("All active trips")},
			{value: "planned", label: __("Planned")},
			{value: "assigned", label: __("Assigned")},
			{value: "loaded", label: __("Loaded")},
			{value: "in_transit", label: __("In transit")},
			{value: "delivered", label: __("Delivered")},
			{value: "exception", label: __("Exception")},
		];

		const options = groups
			.map((row) => `<option value="${utils.escape(row.value)}">${utils.escape(row.label)}</option>`)
			.join("");

		this.container.html(`
			<form class="al-dispatch-filters" data-map-filters>
				<div class="al-dispatch-field">
					<label>${__("Status group")}</label>
					<select name="status_group">${options}</select>
				</div>
				<div class="al-dispatch-field">
					<label>${__("From date")}</label>
					<input type="date" name="from_date" />
				</div>
				<div class="al-dispatch-field">
					<label>${__("To date")}</label>
					<input type="date" name="to_date" />
				</div>
				<div class="al-dispatch-filters-actions">
					<button type="button" class="btn btn-sm btn-primary" data-map-apply>
						${frappe.utils.icon("funnel")}<span>${__("Apply")}</span>
					</button>
				</div>
			</form>
			<div class="al-dispatch-map" data-map-container></div>
			<div data-map-summary style="margin-top:12px"></div>
			<div class="al-dispatch-map-legend" data-map-legend></div>
		`);

		this.$map = this.container.find("[data-map-container]");
		this.$summary = this.container.find("[data-map-summary]");
		this.$legend = this.container.find("[data-map-legend]");
		this.$form = this.container.find("[data-map-filters]");

		this.container.find("[data-map-apply]").on("click", () => this.load());
		this.$form.on("submit", (event) => {
			event.preventDefault();
			this.load();
		});
	},

	load() {
		const me = this;
		const values = {};
		this.$form.serializeArray().forEach((row) => {
			values[row.name] = row.value;
		});

		this.$map.html(
			`<div class="al-dispatch-loading" style="height:100%">
				<span class="al-dispatch-spinner"></span><span>${__("Loading trip map")}</span>
			</div>`
		);

		this.console
			.call({
				method: "dispatch_portal.api.trip_map.get_map_data",
				args: {filters: values},
			})
			.then((response) => me.render_map(response.message || {}))
			.catch((error) => {
				me.$map.empty();
				me.$summary.html(`<div class="al-dispatch-error">${dispatch_portal.utils.server_message(error)}</div>`);
			});
	},

	render_map(data) {
		const utils = dispatch_portal.utils;
		const markers = data.markers || [];

		this.$map.empty();
		this.$summary.html(`
			<div class="al-dispatch-chips">
				<span class="al-dispatch-chip">${__("Trips in range")}<span class="al-dispatch-chip-count">${utils.format_number(
			data.total_trips,
			0
		)}</span></span>
				<span class="al-dispatch-chip">${__("Geolocated")}<span class="al-dispatch-chip-count">${utils.format_number(
			data.located_trips,
			0
		)}</span></span>
				<span class="al-dispatch-chip">${__("Without coordinates")}<span class="al-dispatch-chip-count">${utils.format_number(
			data.unlocated_trips,
			0
		)}</span></span>
			</div>
		`);

		this.$legend.html(
			(data.legend || [])
				.map(
					(row) =>
						`<span class="al-dispatch-chip">${utils.escape(String(row.label).replace(/_/g, " "))}</span>`
				)
				.join("")
		);

		const geolocated = [];
		markers.forEach((marker) => {
			[marker.origin, marker.destination].concat(marker.stops || []).forEach((point) => {
				if (point && point.geolocated) {
					geolocated.push(point);
				}
			});
		});

		if (!geolocated.length) {
			this.$map.html(
				`<div class="al-dispatch-empty" style="height:100%">${__(
					"No Transport Location has coordinates for the selected trips."
				)}</div>`
			);
			return;
		}

		const map_id = frappe.dom.get_unique_id();
		this.$map.html(`<div id="${map_id}" style="height:100%"></div>`);

		this.map = L.map(map_id);
		this.layers.forEach((layer) => this.map.removeLayer(layer));
		this.layers = [];

		const map_defaults = frappe.utils.map_defaults || {};
		const tile_url = (map_defaults.tiles && map_defaults.tiles.default_tile.url) || null;

		if (tile_url) {
			L.Icon.Default.imagePath = map_defaults.image_path;
			this.map.addLayer(
				L.tileLayer(tile_url, (map_defaults.tiles.default_tile.options) || {})
			);
		}

		markers.forEach((marker) => this.draw_trip(marker));
		this.fit_bounds(geolocated);
	},

	draw_trip(marker) {
		const utils = dispatch_portal.utils;
		const path = [marker.origin, marker.destination]
			.concat(marker.stops || [])
			.filter((point) => point && point.geolocated)
			.map((point) => [point.latitude, point.longitude]);

		if (path.length > 1) {
			const polyline = L.polyline(path, {color: "#0E7C86", weight: 3, opacity: 0.7});
			this.map.addLayer(polyline);
			this.layers.push(polyline);
		}

		const endpoints = [
			{point: marker.origin, role: __("Origin")},
			{point: marker.destination, role: __("Destination")},
		].concat(
			(marker.stops || []).map((point) => ({point: point, role: __("Loading stop")}))
		);

		endpoints.forEach((entry) => {
			if (!entry.point || !entry.point.geolocated) {
				return;
			}
			const circle = L.circleMarker([entry.point.latitude, entry.point.longitude], {
				radius: 7,
				color: "#0B2545",
				fillColor: this.marker_color(marker.status),
				fillOpacity: 0.9,
				weight: 2,
			});

			circle.bindPopup(
				`<div class="al-dispatch-popup">
					<div class="al-dispatch-card-head">
						<strong>${utils.escape(marker.trip)}</strong>
						${utils.status_badge(marker.status)}
					</div>
					<p>${utils.escape(entry.role)}: ${utils.escape(entry.point.label)}</p>
					<p>${utils.escape(entry.point.city || "")}</p>
					<p>${utils.escape(String(marker.route || ""))}</p>
					<p>${__("Vehicle")}: ${utils.escape(String(marker.vehicle || "-"))} &middot; ${__(
					"Driver"
				)}: ${utils.escape(String(marker.driver || "-"))}</p>
					<p><a class="al-dispatch-link" href="/app/dispatch-console/trips/${utils.escape(
						marker.trip
					)}">${__("Open trip")}</a></p>
				</div>`
			);

			this.map.addLayer(circle);
			this.layers.push(circle);
		});
	},

	marker_color(status) {
		const colors = {
			PLANNED: "#94A3B8",
			ASSIGNED: "#38BDF8",
			LOADED: "#8B5CF6",
			IN_TRANSIT: "#F59E0B",
			DELIVERED: "#16A34A",
			POD_RECEIVED: "#16A34A",
			EXCEPTION: "#DC2626",
			CLOSED: "#475569",
			CANCELLED: "#B91C1C",
		};
		return colors[status] || "#0E7C86";
	},

	fit_bounds(points) {
		const bounds = L.latLngBounds(
			points.map((point) => [point.latitude, point.longitude])
		);
		this.map.fitBounds(bounds.pad(0.15));
		if (!this.map.getZoom || this.map.getZoom() < 4) {
			this.map.setZoom(6);
		}
	},
};
