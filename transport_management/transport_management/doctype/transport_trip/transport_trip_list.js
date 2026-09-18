frappe.listview_settings["Transport Trip"] = {
	add_fields: [
		"transport_job",
		"trip_date",
		"execution_source",
		"vehicle",
		"hired_vehicle",
		"driver",
		"hired_driver",
		"material",
		"loading_site",
		"unloading_site",
		"planned_quantity",
		"delivered_quantity",
		"status",
	],

	onload(listview) {
		setup_tms_trip_list(listview);
	},

	refresh(listview) {
		setup_tms_trip_list(listview);
	},

	get_indicator(doc) {
		const status = doc.status || "PLANNED";
		const color = {
			PLANNED: "gray",
			ASSIGNED: "blue",
			LOADED: "orange",
			IN_TRANSIT: "purple",
			DELIVERED: "green",
			POD_RECEIVED: "teal",
			CLOSED: "darkgrey",
			CANCELLED: "red",
			EXCEPTION: "orange",
		}[status] || "gray";

		return [trip_status_label(status), color, `status,=,${status}`];
	},

	formatters: {
		vehicle(value, df, doc) {
			return effective_vehicle_display(doc);
		},

		driver(value, df, doc) {
			return effective_driver_display(doc);
		},

		material(value) {
			return trip_text_display(value, "tms-list-material");
		},

		loading_site(value, df, doc) {
			return trip_route_display(doc.loading_site, doc.unloading_site);
		},

		planned_quantity(value) {
			return trip_quantity_display(value);
		},

		delivered_quantity(value) {
			return trip_quantity_display(value);
		},

		status(value) {
			return trip_status_badge(value);
		},
	},
};

function setup_tms_trip_list(listview) {
	if (listview?.page?.wrapper) {
		$(listview.page.wrapper).addClass("tms-transport-trip-list");
	}
	ensure_tms_trip_list_styles();
}

function effective_vehicle_display(doc) {
	const value = doc.execution_source === "HIRED" ? doc.hired_vehicle : doc.vehicle;
	return trip_text_display(value, "tms-list-vehicle");
}

function effective_driver_display(doc) {
	const value = doc.execution_source === "HIRED" ? doc.hired_driver : doc.driver;
	return trip_text_display(value, "tms-list-driver");
}

function trip_route_display(loading_site, unloading_site) {
	const route = [loading_site, unloading_site].filter(Boolean).join(" \u2192 ");

	return trip_text_display(route, "tms-list-route");
}

function trip_quantity_display(value) {
	if (value === undefined || value === null || value === "") {
		return "";
	}

	const number = trip_format_quantity(value);
	return `<span class="tms-list-qty">${number} TON</span>`;
}

function trip_format_quantity(value) {
	return Number(flt(value, 2)).toLocaleString(undefined, {
		minimumFractionDigits: flt(value, 2) % 1 ? 2 : 0,
		maximumFractionDigits: 2,
	});
}

function trip_text_display(value, class_name) {
	const text = value || "";
	const escaped = frappe.utils.escape_html(text);
	return `<span class="${class_name}" title="${escaped}">${escaped}</span>`;
}

function trip_status_badge(value) {
	return `<span class="tms-list-badge tms-${trip_status_color(value)}">${frappe.utils.escape_html(
		trip_status_label(value)
	)}</span>`;
}

function trip_status_label(status) {
	const labels = {
		PLANNED: __("Planned"),
		ASSIGNED: __("Assigned"),
		LOADED: __("Loaded"),
		IN_TRANSIT: __("In Transit"),
		DELIVERED: __("Delivered"),
		POD_RECEIVED: __("POD Received"),
		CLOSED: __("Closed"),
		CANCELLED: __("Cancelled"),
		EXCEPTION: __("Exception"),
	};
	return labels[status] || __(status || "");
}

function trip_status_color(status) {
	const colors = {
		PLANNED: "gray",
		ASSIGNED: "blue",
		LOADED: "orange",
		IN_TRANSIT: "purple",
		DELIVERED: "green",
		POD_RECEIVED: "teal",
		CLOSED: "dark",
		CANCELLED: "red",
		EXCEPTION: "orange",
	};
	return colors[status] || "gray";
}

function ensure_tms_trip_list_styles() {
	if (document.getElementById("tms-list-view-styles")) {
		return;
	}

	$(`<style id="tms-list-view-styles">
		.tms-list-route {
			display: inline-block;
			max-width: 340px;
			overflow: hidden;
			text-overflow: ellipsis;
			vertical-align: bottom;
			white-space: nowrap;
		}
		.tms-list-customer,
		.tms-list-reference,
		.tms-list-vehicle,
		.tms-list-driver,
		.tms-list-material {
			display: inline-block;
			max-width: 180px;
			overflow: hidden;
			text-overflow: ellipsis;
			vertical-align: bottom;
			white-space: nowrap;
		}
		.tms-list-qty {
			font-variant-numeric: tabular-nums;
			white-space: nowrap;
		}
		.tms-transport-job-list .list-row,
		.tms-transport-trip-list .list-row {
			min-height: 34px;
		}
		.tms-transport-job-list .list-row-col,
		.tms-transport-trip-list .list-row-col {
			align-items: center;
			padding-bottom: 6px;
			padding-top: 6px;
		}
		.tms-list-badge {
			border-radius: 999px;
			display: inline-block;
			font-size: 11px;
			font-weight: 600;
			line-height: 1;
			padding: 4px 7px;
			white-space: nowrap;
		}
		.tms-blue { background: #e7f0ff; color: #1f5fbf; }
		.tms-orange { background: #fff4db; color: #97620c; }
		.tms-green { background: #e8f7ee; color: #1f7a3a; }
		.tms-gray { background: #f1f3f5; color: #5b6470; }
		.tms-red { background: #ffe8e8; color: #b42318; }
		.tms-purple { background: #eee9ff; color: #5b3bc4; }
		.tms-teal { background: #e4f7f4; color: #107569; }
		.tms-dark { background: #e5e7eb; color: #374151; }
	</style>`).appendTo("head");
}
