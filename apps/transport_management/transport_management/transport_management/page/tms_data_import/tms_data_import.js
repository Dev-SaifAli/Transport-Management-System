frappe.pages["tms-data-import"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Transport Management / Data Import"),
		single_column: true,
	});

	const state = {
		file_name: null,
		file_label: null,
		import_type: "Transport Locations",
		last_preview: null,
	};

	page.set_primary_action(__("Dry Run / Preview"), () => run_preview(), "search");
	page.add_action_item(__("Back to Transport Management"), () => frappe.set_route("transport-management"));

	$(page.body).html(`
		<div class="tms-data-import">
			<div class="row">
				<div class="col-lg-4">
					<div class="frappe-card p-4">
						<div class="form-group">
							<label class="control-label">${__("Import Type")}</label>
							<select class="form-control" data-field="import-type">
								<option value="Transport Locations">${__("Transport Locations")}</option>
								<option value="Owned Trucks">${__("Owned Trucks")}</option>
								<option value="Materials">${__("Materials")}</option>
							</select>
						</div>
						<div class="form-group mt-4">
							<label class="control-label">${__("Source File")}</label>
							<div data-field="file-uploader"></div>
							<div class="text-muted small mt-2" data-field="selected-file">${__("No file uploaded")}</div>
						</div>
						<div class="mt-4 d-flex flex-wrap gap-2">
							<button class="btn btn-primary btn-sm" data-action="preview">${__("Dry Run / Preview")}</button>
							<button class="btn btn-default btn-sm" data-action="refresh">${__("Refresh")}</button>
							<button class="btn btn-success btn-sm" data-action="import" disabled>${__("Import NEW Records")}</button>
						</div>
					</div>
				</div>
				<div class="col-lg-8">
					<div class="frappe-card p-4">
						<h5 class="m-0">${__("Preview Summary")}</h5>
						<div class="row mt-3" data-field="summary"></div>
					</div>
				</div>
			</div>
			<div class="frappe-card p-4 mt-4">
				<div class="d-flex justify-content-between align-items-center mb-3">
					<h5 class="m-0">${__("Preview")}</h5>
					<span class="text-muted small" data-field="preview-note">${__("Upload a file and run preview.")}</span>
				</div>
				<div class="table-responsive">
					<table class="table table-bordered table-sm">
						<thead data-field="preview-head"></thead>
						<tbody data-field="preview-rows">
							<tr><td colspan="6" class="text-muted">${__("No preview yet.")}</td></tr>
						</tbody>
					</table>
				</div>
			</div>
			<div class="frappe-card p-4 mt-4 hide" data-field="result-card">
				<h5 class="m-0">${__("Import Result")}</h5>
				<div class="row mt-3" data-field="result-summary"></div>
			</div>
		</div>
	`);

	const $body = $(page.body);
	const $import_button = $body.find('[data-action="import"]');

	new frappe.ui.FileUploader({
		wrapper: $body.find('[data-field="file-uploader"]'),
		allow_multiple: false,
		make_attachments_public: false,
		restrictions: {
			allowed_file_types: [".xlsx", ".csv"],
		},
		on_success(file_doc) {
			state.file_name = file_doc.name;
			state.file_label = file_doc.file_name || file_doc.name;
			state.last_preview = null;
			$import_button.prop("disabled", true);
			$body.find('[data-field="selected-file"]').text(state.file_label);
			clear_result();
		},
	});

	$body.find('[data-field="import-type"]').on("change", function () {
		state.import_type = $(this).val();
		state.last_preview = null;
		$import_button.prop("disabled", true);
		clear_result();
		render_empty_preview();
	});

	$body.find('[data-action="preview"]').on("click", () => run_preview());
	$body.find('[data-action="refresh"]').on("click", () => {
		if (state.file_name) {
			run_preview();
		}
	});
	$import_button.on("click", () => run_actual_import());

	function ensure_file() {
		if (!state.file_name) {
			frappe.msgprint(__("Please upload an .xlsx or .csv file first."));
			return false;
		}
		return true;
	}

	function run_preview() {
		if (!ensure_file()) return;
		clear_result();
		frappe.call({
			method: "transport_management.imports.base_importer.dry_run_import",
			args: {
				import_type: state.import_type,
				file_name: state.file_name,
			},
			freeze: true,
			freeze_message: __("Reading file..."),
			callback(r) {
				state.last_preview = r.message;
				render_preview(r.message);
				const summary = r.message.summary || {};
				$import_button.prop("disabled", Boolean(summary.conflicts || summary.conflict));
			},
		});
	}

	function run_actual_import() {
		if (!ensure_file() || !state.last_preview) return;
		frappe.confirm(
			__("Import will create only NEW records for the selected import type. Existing records and updates will be skipped."),
			() => {
				frappe.call({
					method: "transport_management.imports.base_importer.run_import",
					args: {
						import_type: state.import_type,
						file_name: state.file_name,
					},
					freeze: true,
					freeze_message: __("Importing..."),
					callback(r) {
						render_preview(r.message);
						render_result(r.message);
						$import_button.prop("disabled", true);
					},
				});
			}
		);
	}

	function render_preview(result) {
		const summary = result.summary || {};
		render_summary($body.find('[data-field="summary"]'), get_summary_rows(summary));

		const rows = [];
		render_table_header(result.import_type);
		(result.records || []).forEach((record) => rows.push(render_record_row(result.import_type, record)));
		(result.invalid_rows || []).forEach((row) => {
			rows.push(render_invalid_row(result.import_type, row));
		});

		$body.find('[data-field="preview-rows"]').html(
			rows.length ? rows.join("") : `<tr><td colspan="6" class="text-muted">${__("No rows found.")}</td></tr>`
		);
		$body.find('[data-field="preview-note"]').text(
			__("Preview generated for {0}", [result.file_name || state.file_label || ""])
		);
	}

	function render_result(result) {
		const summary = result.summary || {};
		$body.find('[data-field="result-card"]').removeClass("hide");
		render_summary($body.find('[data-field="result-summary"]'), [
			["Created", summary.created],
			["Created Types", summary.created_truck_types],
			["Compatibility Rows", summary.created_compatibility_rows],
			["Skipped", summary.skipped],
			["Failed", summary.failed],
			["Final Count", summary.final_count],
		]);
	}

	function clear_result() {
		$body.find('[data-field="result-card"]').addClass("hide");
		$body.find('[data-field="result-summary"]').empty();
	}

	function render_summary($target, rows) {
		$target.html(
			rows.map(([label, value]) => `
				<div class="col-sm-3 col-6 mb-3">
					<div class="text-muted small">${__(label)}</div>
					<div class="h4 m-0">${frappe.utils.escape_html(value == null ? 0 : value)}</div>
				</div>
			`).join("")
		);
	}

	function get_summary_rows(summary) {
		if (state.import_type === "Owned Trucks") {
			return [
				["Source Rows", summary.source_rows],
				["Valid Rows", summary.valid_rows],
				["Unique Trucks", summary.unique_trucks],
				["NEW", summary.new],
				["EXISTS", summary.exists],
				["UPDATE_TYPE", summary.update_type],
				["OWNERSHIP_CONFLICT", summary.ownership_conflict],
				["DUPLICATE_SOURCE", summary.duplicate_source],
				["INVALID", summary.invalid],
				["CONFLICT", summary.conflict],
			];
		}
		if (state.import_type === "Materials") {
			return [
				["Source Rows", summary.source_rows],
				["Valid Rows", summary.valid_rows],
				["Unique Materials", summary.unique_materials],
				["NEW", summary.new],
				["EXISTS", summary.exists],
				["UPDATE_COMPATIBILITY", summary.update_compatibility],
				["DUPLICATE_SOURCE", summary.duplicate_source],
				["INVALID", summary.invalid],
				["CONFLICT", summary.conflict],
			];
		}
		return [
			["Source Rows", summary.source_rows],
			["Valid Rows", summary.valid_rows],
			["Unique Records", summary.unique_locations],
			["NEW", summary.new],
			["EXISTS", summary.exists],
			["UPDATE_USAGE", summary.update_usage],
			["CONFLICT", summary.conflicts],
			["INVALID", summary.invalid],
		];
	}

	function render_table_header(import_type) {
		let headers;
		if (import_type === "Owned Trucks") {
			headers = ["Source Plate", "Normalized Plate", "Truck Type", "Existing Truck", "Existing Type", "Status", "Error / Remark"];
		} else if (import_type === "Materials") {
			headers = ["Material Name", "Allowed Truck Type", "Active", "Existing Material", "Existing Types", "Status", "Error / Remark"];
		} else {
			headers = ["Location Name", "Location Usage", "Location Type", "Country", "Status", "Error / Remark"];
		}
		$body.find('[data-field="preview-head"]').html(
			`<tr>${headers.map((label) => `<th>${__(label)}</th>`).join("")}</tr>`
		);
	}

	function render_record_row(import_type, record) {
		if (import_type === "Owned Trucks") {
			return `
				<tr>
					<td>${frappe.utils.escape_html(record.source_plate || "")}</td>
					<td>${frappe.utils.escape_html(record.normalized_plate || "")}</td>
					<td>${frappe.utils.escape_html(record.source_truck_type || "")}</td>
					<td>${frappe.utils.escape_html(record.existing_truck || "")}</td>
					<td>${frappe.utils.escape_html(record.existing_type || "")}</td>
					<td>${frappe.utils.escape_html(record.status || "")}</td>
					<td>${frappe.utils.escape_html(record.error || "")}</td>
				</tr>
			`;
		}
		if (import_type === "Materials") {
			return `
				<tr>
					<td>${frappe.utils.escape_html(record.material_name || "")}</td>
					<td>${frappe.utils.escape_html(record.truck_type || "")}</td>
					<td>${frappe.utils.escape_html(record.active == null ? "" : record.active)}</td>
					<td>${frappe.utils.escape_html(record.existing_material || "")}</td>
					<td>${frappe.utils.escape_html((record.existing_allowed_truck_types || []).join(", "))}</td>
					<td>${frappe.utils.escape_html(record.status || "")}</td>
					<td>${frappe.utils.escape_html(record.error || "")}</td>
				</tr>
			`;
		}
		const remark = record.existing_name
			? __("Existing: {0} ({1})", [record.existing_name, record.existing_usage || __("blank")])
			: "";
		return `
			<tr>
				<td>${frappe.utils.escape_html(record.location || "")}</td>
				<td>${frappe.utils.escape_html(record.location_usage || "")}</td>
				<td>${frappe.utils.escape_html(record.location_type || "")}</td>
				<td>${frappe.utils.escape_html(record.country || "")}</td>
				<td>${frappe.utils.escape_html(record.status || "")}</td>
				<td>${frappe.utils.escape_html(record.error || remark || "")}</td>
			</tr>
		`;
	}

	function render_invalid_row(import_type, row) {
		if (import_type === "Owned Trucks" || import_type === "Materials") {
			return `
				<tr>
					<td>${frappe.utils.escape_html(row.value || __("Row {0}", [row.row_number]))}</td>
					<td></td>
					<td></td>
					<td></td>
					<td></td>
					<td>INVALID</td>
					<td>${frappe.utils.escape_html(row.reason || "")}</td>
				</tr>
			`;
		}
		return `
			<tr>
				<td>${frappe.utils.escape_html(row.value || __("Row {0}", [row.row_number]))}</td>
				<td></td>
				<td></td>
				<td></td>
				<td>INVALID</td>
				<td>${frappe.utils.escape_html(row.reason || "")}</td>
			</tr>
		`;
	}

	function render_empty_preview() {
		render_table_header(state.import_type);
		const colspan = state.import_type === "Owned Trucks" || state.import_type === "Materials" ? 7 : 6;
		$body.find('[data-field="preview-rows"]').html(
			`<tr><td colspan="${colspan}" class="text-muted">${__("Upload a file and run preview.")}</td></tr>`
		);
		$body.find('[data-field="summary"]').empty();
	}

	render_empty_preview();
};
