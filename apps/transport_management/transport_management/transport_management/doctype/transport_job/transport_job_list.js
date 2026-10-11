frappe.listview_settings["Transport Job"] = {
	add_fields: [
		"customer",
		"material",
		"loading_site",
		"unloading_site",
		"requested_quantity",
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

		loading_site(value) {
			return text_display(value);
		},

		unloading_site(value) {
			return text_display(value);
		},

		requested_quantity(value) {
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
	return frappe.utils.escape_html(value || "");
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
				padding-bottom: 6px;
				padding-left: 10px;
				padding-right: 10px;
				padding-top: 6px;
				min-width: 0;
			}

			.tms-transport-job-list .list-subject {
				min-width: 135px;
				padding-right: 12px;
			}

			/* Customer */
			.tms-transport-job-list
			.list-row-col[data-fieldname="customer"] {
				flex: 1.35 1 230px;
				min-width: 210px;
				max-width: 320px;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}

			/* Billing Status */
			.tms-transport-job-list
			.list-row-col[data-fieldname="billing_status"] {
				flex: 0 0 145px;
				white-space: nowrap;
			}

			/* Material */
			.tms-transport-job-list
			.list-row-col[data-fieldname="material"] {
				flex: 1 1 170px;
				min-width: 150px;
				max-width: 230px;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}

			/* Quantities */
			.tms-transport-job-list
			.list-row-col[data-fieldname="requested_quantity"] {
				flex: 0 0 110px;
				white-space: nowrap;
			}

			/* Route fields */
			.tms-transport-job-list
			.list-row-col[data-fieldname="loading_site"],
			.tms-transport-job-list
			.list-row-col[data-fieldname="unloading_site"] {
				flex: 1 1 165px;
				min-width: 150px;
				max-width: 230px;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}

			/* Status */
			.tms-transport-job-list
			.list-row-col[data-fieldname="status"] {
				min-width: 110px;
				white-space: nowrap;
			}

			/* Sales Order */
			.tms-transport-job-list
			.list-row-col[data-fieldname="sale_order_reference"] {
				flex: 0 1 165px;
				min-width: 145px;
				max-width: 190px;
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
