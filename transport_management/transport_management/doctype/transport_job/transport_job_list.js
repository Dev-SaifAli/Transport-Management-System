frappe.listview_settings["Transport Job"] = {
	add_fields: [
		"customer",
		"material",
		"loading_site",
		"unloading_site",
		"requested_quantity",
		"delivered_quantity",
		"remaining_quantity",
		"status",
		"billing_status",
		"sale_order_reference",
	],

	onload(listview) {
		setup_tms_job_list(listview);
	},

	refresh(listview) {
		setup_tms_job_list(listview);
	},

	get_indicator(doc) {
		const status = doc.status || "Draft";

		const color = {
			Draft: "blue",
			Ready: "blue",
			"In Progress": "orange",
			Completed: "green",
			Cancelled: "red",
		}[status] || "gray";

		return [__(status), color, `status,=,${status}`];
	},

	formatters: {
		customer(value) {
			return text_display(value);
		},

		material(value) {
			return text_display(value);
		},

		loading_site(value, df, doc) {
			return route_display(doc.loading_site, doc.unloading_site);
		},

		requested_quantity(value) {
			return quantity_display(value);
		},

		delivered_quantity(value) {
			return quantity_display(value);
		},

		remaining_quantity(value) {
			return quantity_display(value);
		},

		status(value) {
			return value ? __(value) : "";
		},

		billing_status(value) {
			return value ? __(value) : "";
		},

		sale_order_reference(value) {
			return text_display(value);
		},
	},
};

function setup_tms_job_list(listview) {
	if (listview?.page?.wrapper) {
		$(listview.page.wrapper).addClass("tms-transport-job-list");
	}

	ensure_tms_list_styles();
}

function route_display(loading_site, unloading_site) {
	return [loading_site, unloading_site]
		.filter(Boolean)
		.join(" → ");
}

function quantity_display(value) {
	if (value === undefined || value === null || value === "") {
		return "";
	}

	return `${format_quantity(value)} TON`;
}

function format_quantity(value) {
	const number = flt(value, 2);

	return Number(number).toLocaleString(undefined, {
		minimumFractionDigits: number % 1 ? 2 : 0,
		maximumFractionDigits: 2,
	});
}

function text_display(value) {
	return value || "";
}

function ensure_tms_list_styles() {
	if (document.getElementById("tms-job-list-view-styles")) {
		return;
	}

	$(`
		<style id="tms-job-list-view-styles">

			/* Compact rows */
			.tms-transport-job-list .list-row {
				min-height: 34px;
			}

			.tms-transport-job-list .list-row-col {
				align-items: center;
				padding-top: 6px;
				padding-bottom: 6px;
			}

			/* Customer */
			.tms-transport-job-list
			.list-row-col[data-fieldname="customer"] {
				min-width: 190px;
				max-width: 240px;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}

			/* Material */
			.tms-transport-job-list
			.list-row-col[data-fieldname="material"] {
				min-width: 140px;
				max-width: 180px;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}

			/* Route */
			.tms-transport-job-list
			.list-row-col[data-fieldname="loading_site"] {
				min-width: 280px;
				max-width: 360px;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}

			/* Quantities */
			.tms-transport-job-list
			.list-row-col[data-fieldname="requested_quantity"],
			.tms-transport-job-list
			.list-row-col[data-fieldname="delivered_quantity"],
			.tms-transport-job-list
			.list-row-col[data-fieldname="remaining_quantity"] {
				min-width: 115px;
				white-space: nowrap;
			}

			/* Status */
			.tms-transport-job-list
			.list-row-col[data-fieldname="status"] {
				min-width: 110px;
				white-space: nowrap;
			}

			/* Billing Status */
			.tms-transport-job-list
			.list-row-col[data-fieldname="billing_status"] {
				min-width: 150px;
				white-space: nowrap;
			}

			/* Sales Order */
			.tms-transport-job-list
			.list-row-col[data-fieldname="sale_order_reference"] {
				min-width: 150px;
				max-width: 180px;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}

			/* Prevent awkward wrapping inside list values */
			.tms-transport-job-list .list-row-col .ellipsis {
				white-space: nowrap;
			}

		</style>
	`).appendTo("head");
}