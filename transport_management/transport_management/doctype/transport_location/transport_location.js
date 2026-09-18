// Copyright (c) 2026, Digital Data Enterprises and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Location", {
	refresh(frm) {
		enforce_form_display(frm);
		set_default_country(frm);
		render_location_map(frm);
	},

	latitude(frm) {
		sync_marker_from_fields(frm);
	},

	longitude(frm) {
		sync_marker_from_fields(frm);
	},
});

const UAE_CENTER = [24.4539, 54.3773];
const UAE_ZOOM = 7;
const LEAFLET_JS = "/assets/frappe/js/lib/leaflet/leaflet.js";
const LEAFLET_CSS = "/assets/frappe/js/lib/leaflet/leaflet.css";
let leaflet_promise = null;

function enforce_form_display(frm) {
	frm.set_df_property("location", "hidden", 0);
	frm.set_df_property("supplier", "hidden", 1);
	frm.toggle_display("location", true);
	frm.toggle_display("supplier", false);
	frm.refresh_field("location");
}

function set_default_country(frm) {
	if (frm.is_new() && !frm.doc.country) {
		frm.set_value("country", "United Arab Emirates");
	}
}

function render_location_map(frm) {
	const field = frm.get_field("map_html");
	if (!field) return;
	if (frm.tms_location_map?.map) {
		frm.tms_location_map.map.remove();
		frm.tms_location_map = null;
	}
	field.$wrapper.html(`
		<div class="tms-location-map-tool">
			<div class="input-group mb-2">
				<input class="form-control" data-field="location-search" placeholder="${__("Search Location")}">
				<button class="btn btn-default" type="button" data-action="search-location">${__("Search")}</button>
				<button class="btn btn-default" type="button" data-action="update-map">${__("Update Map")}</button>
			</div>
			<div data-field="search-results" class="mb-2"></div>
			<div data-field="map" style="height: 430px; border: 1px solid var(--border-color); border-radius: 6px;"></div>
		</div>
	`);
	load_leaflet()
		.then(() => initialize_map(frm))
		.catch(() => {
			field.$wrapper.find('[data-field="map"]').html(
				`<div class="text-muted p-3">${__("Map library is temporarily unavailable. You can still enter latitude and longitude manually.")}</div>`
			);
		});
}

function load_leaflet() {
	if (window.L) return Promise.resolve();
	if (leaflet_promise) return leaflet_promise;
	if (!$('link[href="' + LEAFLET_CSS + '"]').length) {
		$(`<link rel="stylesheet" href="${LEAFLET_CSS}">`).appendTo("head");
	}
	leaflet_promise = frappe.require(LEAFLET_JS);
	return leaflet_promise;
}

function initialize_map(frm) {
	const wrapper = frm.get_field("map_html").$wrapper;
	const map_node = wrapper.find('[data-field="map"]')[0];
	const existing = get_field_coordinates(frm);
	const center = existing || UAE_CENTER;
	const zoom = existing ? 13 : UAE_ZOOM;
	const map = L.map(map_node).setView(center, zoom);
	L.Icon.Default.imagePath = frappe.utils.map_defaults?.image_path || "/assets/frappe/images/leaflet/";
	L.tileLayer(
		frappe.utils.map_defaults?.tiles?.default_tile?.url || "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
		frappe.utils.map_defaults?.tiles?.default_tile?.options || {
			maxZoom: 19,
			attribution: "&copy; OpenStreetMap contributors",
		}
	).addTo(map);
	frm.tms_location_map = { map, marker: null };
	if (existing) {
		set_marker(frm, existing[0], existing[1], false);
	}
	map.on("click", (event) => {
		set_coordinates(frm, event.latlng.lat, event.latlng.lng, true);
	});
	wrapper.find('[data-action="search-location"]').on("click", () => search_location(frm));
	wrapper.find('[data-action="update-map"]').on("click", () => update_map_from_fields(frm));
	wrapper.find('[data-field="location-search"]').on(
		"input",
		frappe.utils.debounce(() => search_location(frm), 600)
	);
	setTimeout(() => map.invalidateSize(), 200);
}

function search_location(frm) {
	const wrapper = frm.get_field("map_html").$wrapper;
	const query = wrapper.find('[data-field="location-search"]').val();
	if (!query) return;
	frappe.call({
		method: "transport_management.transport_management.doctype.transport_location.transport_location.search_location",
		args: { query, country: frm.doc.country || "United Arab Emirates" },
		callback(r) {
			render_results(frm, r.message || []);
		},
		error() {
			frappe.msgprint(__("Location search is temporarily unavailable. You can still select the location manually on the map."));
		},
	});
}

function render_results(frm, results) {
	const target = frm.get_field("map_html").$wrapper.find('[data-field="search-results"]');
	if (!results.length) {
		target.html(`<div class="text-muted small">${__("No matching locations found.")}</div>`);
		return;
	}
	target.html(results.map((row, index) => `
		<button type="button" class="btn btn-xs btn-default mr-1 mb-1" data-index="${index}">
			${frappe.utils.escape_html(row.display_name || "")}
		</button>
	`).join(""));
	target.find("button").on("click", function () {
		apply_geocode_result(frm, results[$(this).data("index")]);
	});
}

function apply_geocode_result(frm, result) {
	if (!result) return;
	set_coordinates(frm, result.latitude, result.longitude, true);
}

function set_coordinates(frm, latitude, longitude, should_reverse) {
	frm.set_value("latitude", flt(latitude, 8));
	frm.set_value("longitude", flt(longitude, 8));
	set_marker(frm, latitude, longitude, true);
	if (should_reverse) {
		reverse_geocode(frm, latitude, longitude);
	}
}

function reverse_geocode(frm, latitude, longitude) {
	frappe.call({
		method: "transport_management.transport_management.doctype.transport_location.transport_location.reverse_geocode",
		args: { latitude, longitude },
		callback(r) {
			apply_address_fields(frm, r.message || {});
		},
	});
}

function apply_address_fields(frm, result) {
	const updates = [];
	if (result.city) updates.push(frm.set_value("city", result.city));
	if (result.area_zone) updates.push(frm.set_value("area_zone", result.area_zone));
	if (result.country && !frm.doc.country) updates.push(frm.set_value("country", result.country));
	if (updates.length) {
		Promise.all(updates).then(() => {
			frm.refresh_field("city");
			frm.refresh_field("area_zone");
			frm.refresh_field("country");
		});
	}
}

function set_marker(frm, latitude, longitude, center) {
	if (!frm.tms_location_map || !window.L) return;
	const latlng = [flt(latitude, 8), flt(longitude, 8)];
	if (!frm.tms_location_map.marker) {
		frm.tms_location_map.marker = L.marker(latlng, { draggable: true }).addTo(frm.tms_location_map.map);
		frm.tms_location_map.marker.on("dragend", () => {
			const point = frm.tms_location_map.marker.getLatLng();
			set_coordinates(frm, point.lat, point.lng, true);
		});
	} else {
		frm.tms_location_map.marker.setLatLng(latlng);
	}
	if (center) {
		frm.tms_location_map.map.setView(latlng, 13);
	}
}

function sync_marker_from_fields(frm) {
	const coordinates = get_field_coordinates(frm);
	if (coordinates) {
		set_marker(frm, coordinates[0], coordinates[1], true);
	}
}

function update_map_from_fields(frm) {
	const coordinates = get_field_coordinates(frm);
	if (coordinates) {
		set_marker(frm, coordinates[0], coordinates[1], true);
		reverse_geocode(frm, coordinates[0], coordinates[1]);
	}
}

function get_field_coordinates(frm) {
	if (frm.doc.latitude === undefined || frm.doc.latitude === null || frm.doc.latitude === "") return null;
	if (frm.doc.longitude === undefined || frm.doc.longitude === null || frm.doc.longitude === "") return null;
	return [flt(frm.doc.latitude, 8), flt(frm.doc.longitude, 8)];
}
