// Verification section of the AL RANA Dispatch console.
// AI extraction is advisory: only values the verifier explicitly accepts are
// written to the Transport Trip, and only documentation fields are writable.

frappe.provide("dispatch_portal.views");

dispatch_portal.views.verification = {
	render(context) {
		this.container = context.container;
		this.console = context.console;
		this.permissions = context.permissions || {};
		this.state = {start: 0, page_length: 20, total: 0, document_type: "", selected: null};

		if (!this.permissions.is_verifier) {
			this.container.html(
				`<div class="al-dispatch-empty">${__(
					"You are not authorised to verify transport trip documents."
				)}</div>`
			);
			return;
		}

		context.console.set_actions([
			{label: __("Refresh"), icon: "rotate-cw", onClick: () => this.load()},
		]);

		this.render_filters();
		this.load();
	},

	render_filters() {
		const utils = dispatch_portal.utils;
		const me = this;

		frappe
			.call({method: "dispatch_portal.api.verification.get_document_types", freeze: false})
			.then((response) => {
				const types = response.message || [];
				const options = [`<option value="">${__("All document types")}</option>`]
					.concat(
						types.map(
							(row) =>
								`<option value="${utils.escape(row.value)}" ${
									me.state.document_type === row.value ? "selected" : ""
								}>${utils.escape(row.label)}</option>`
						)
					)
					.join("");

				me.container.html(`
					<form class="al-dispatch-filters" data-doc-filters>
						<div class="al-dispatch-field">
							<label>${__("Document type")}</label>
							<select name="document_type">${options}</select>
						</div>
						<div class="al-dispatch-filters-actions">
							<button type="button" class="btn btn-sm btn-primary" data-doc-apply>
								${frappe.utils.icon("funnel")}<span>${__("Apply")}</span>
							</button>
						</div>
					</form>
					<div data-doc-summary style="margin-bottom:14px"></div>
					<div class="al-dispatch-split">
						<div data-doc-queue></div>
						<div data-doc-detail></div>
					</div>
				`);

				me.$queue = me.container.find("[data-doc-queue]");
				me.$detail = me.container.find("[data-doc-detail]");
				me.$summary = me.container.find("[data-doc-summary]");

				me.container.find("[data-doc-apply]").on("click", () => {
					me.state.document_type = me.container.find("select[name=document_type]").val();
					me.state.start = 0;
					me.fetch_queue();
				});
				me.fetch_queue();
			});
	},

	load() {
		this.render_filters();
	},

	fetch_queue() {
		const me = this;
		this.console.show_loading(__("Loading review queue"));
		this.console
			.call({
				method: "dispatch_portal.api.verification.get_verification_queue",
				args: {
					filters: {document_type: this.state.document_type},
					start: this.state.start,
					page_length: this.state.page_length,
				},
			})
			.then((response) => me.render_queue(response.message || {}))
			.catch((error) => this.console.show_error(error));
	},

	render_queue(data) {
		const utils = dispatch_portal.utils;
		const documents = data.documents || [];
		this.state.total = data.total || 0;

		const rows = documents.map((row) => [
			`<a class="al-dispatch-link" data-document="${utils.escape(row.name)}">${utils.escape(
				row.transport_trip
			)}</a>`,
			utils.escape(row.document_type_label),
			utils.escape(row.document_type),
			utils.escape(row.upload_source),
			utils.format_datetime(row.uploaded_at),
			utils.verification_badge(row.verification_status),
			`<button type="button" class="btn btn-xs btn-primary" data-review="${utils.escape(
				row.name
			)}">${__("Review")}</button>`,
		]);

		this.$queue.html(
			utils.table_html(
				[
					{label: __("Trip")},
					{label: __("Type")},
					{label: __("Code")},
					{label: __("Source")},
					{label: __("Uploaded")},
					{label: __("Status")},
					{label: __("Actions"), actions: true},
				],
				rows.length ? rows : []
			)
		);

		if (!rows.length) {
			this.$queue.html(utils.empty_state(__("No documents are waiting for review.")));
		}

		this.$queue.find("[data-review], [data-document]").on("click", (event) => {
			const target = $(event.currentTarget);
			this.open_document(target.attr("data-review") || target.attr("data-document"));
		});

		frappe
			.call({method: "dispatch_portal.api.verification.get_verification_summary", freeze: false})
			.then((response) => this.render_summary(response.message || {}))
			.catch(() => {});
	},

	render_summary(summary) {
		const utils = dispatch_portal.utils;
		this.$summary.html(
			`<div class="al-dispatch-chips">
				<span class="al-dispatch-chip">${__("Pending review")}<span class="al-dispatch-chip-count">${utils.format_number(
				summary.pending_review,
				0
			)}</span></span>
				<span class="al-dispatch-chip">${__("Approved")}<span class="al-dispatch-chip-count">${utils.format_number(
				summary.approved,
				0
			)}</span></span>
				<span class="al-dispatch-chip">${__("Rejected")}<span class="al-dispatch-chip-count">${utils.format_number(
				summary.rejected,
				0
			)}</span></span>
			</div>`
		);
	},

	open_document(document_name) {
		const me = this;
		this.$detail.html(
			`<div class="al-dispatch-loading"><span class="al-dispatch-spinner"></span><span>${__(
				"Loading document"
			)}</span></div>`
		);

		this.console
			.call({
				method: "dispatch_portal.api.verification.get_verification_document",
				args: {document_name: document_name},
			})
			.then((response) => me.render_document(response.message || {}))
			.catch((error) => {
				me.$detail.html(
					`<div class="al-dispatch-error">${dispatch_portal.utils.server_message(error)}</div>`
				);
			});
	},

	render_document(data) {
		const utils = dispatch_portal.utils;
		const document = data.document || {};
		const candidates = data.candidates || [];
		const trip = data.trip || {};
		const writable = candidates.filter((row) => row.can_write_trip);

		const contextRows = [
			[__("Trip"), utils.text(trip.trip)],
			[__("Status"), utils.status_badge(trip.status)],
			[__("Customer"), utils.text(trip.customer)],
			[__("Route"), utils.text(trip.loading_site) + " -> " + utils.text(trip.unloading_site)],
			[__("Trip Date"), utils.format_date(trip.trip_date)],
		];

		const candidate_html = candidates.length
			? candidates.map((row) => this.candidate_html(row)).join("")
			: utils.empty_state(__("This document has no extracted values."));

		const infoRows = [
			[__("Document"), utils.escape(document.name)],
			[__("Type"), utils.escape(document.document_type_label)],
			[__("Upload Source"), utils.escape(document.upload_source)],
			[__("Uploaded At"), utils.format_datetime(document.uploaded_at)],
			[__("Uploaded By Driver"), utils.text(document.uploaded_by_driver)],
			[__("AI Status"), utils.escape(document.ai_status)],
			[
				__("AI Confidence"),
				document.ai_confidence ? utils.format_number(document.ai_confidence, 1) + " %" : "-",
			],
			[__("Verification"), utils.verification_badge(document.verification_status)],
			[__("Verified By"), utils.text(document.verified_by)],
			[__("Verified At"), utils.format_datetime(document.verified_at)],
			[__("Review Notes"), utils.text(document.review_notes)],
			[
				__("Attachment"),
				document.file
					? `<a class="al-dispatch-link" href="${utils.escape(document.file)}" target="_blank">${__(
							"Open file"
					  )}</a>`
					: "<span class=\"al-dispatch-muted\">-</span>",
			],
		];

		const can_apply = data.permissions && data.permissions.can_apply;
		const already_reviewed = document.verification_status !== "PENDING_REVIEW";

		this.$detail.html(`
			<section class="al-dispatch-panel">
				<header class="al-dispatch-panel-head">
					<div>
						<h3 class="al-dispatch-panel-title">${utils.escape(document.document_type_label)}</h3>
						<p class="al-dispatch-panel-sub">${utils.escape(trip.trip || "")}</p>
					</div>
					${utils.verification_badge(document.verification_status)}
				</header>
				<div class="al-dispatch-panel-body">
					<div class="al-dispatch-split">
						${utils.table_html(
							[
								{label: __("Field")},
								{label: __("Value")},
							],
							infoRows
						)}
						${utils.panel(__("Trip Context"), "", utils.table_html([{label: __("Field")}, {label: __("Value")}], contextRows))}
					</div>

					${utils.panel(
						__("AI Extraction"),
						__("Extracted values are suggestions and never overwrite trip data on their own"),
						candidate_html
					)}

					${
						already_reviewed
							? `<div class="al-dispatch-empty">${__(
									"This document has already been reviewed."
							  )}</div>`
							: writable.length
							? `<div style="display:flex;gap:8px">
									<button type="button" class="btn btn-sm btn-primary" data-apply-review>
										${__("Apply selected values")}
									</button>
									<button type="button" class="btn btn-sm btn-default" data-reject-review>
										${__("Reject")}
									</button>
								</div>
								<p class="al-dispatch-muted" style="margin:8px 0 0;font-size:12px">
									${__(
										"Only the checked documentation fields are written to the Transport Trip. Trip status, quantities, rates, vehicle, driver, material and locations are never changed by verification."
									)}
								</p>`
							: `<div class="al-dispatch-empty">${__(
									"This document has no values that may be applied to the trip."
							  )}</div>`
					}
					${
						can_apply && already_reviewed
							? `<div style="margin-top:10px">
									<button type="button" class="btn btn-xs btn-default" data-reset-review>${__(
										"Send back to the review queue"
									)}</button>
								</div>`
							: ""
					}
				</div>
			</section>
		`);

		const me = this;
		this.$detail.find("[data-apply-review]").on("click", () => me.apply_review(document));
		this.$detail.find("[data-reject-review]").on("click", () => me.reject_review(document));
		this.$detail.find("[data-reset-review]").on("click", () => {
			frappe
				.call({
					method: "dispatch_portal.api.verification.reset_document_review",
					args: {document_name: document.name},
					btn: me.$detail.find("[data-reset-review]"),
				})
				.then(() => {
					frappe.show_alert({message: __("Document returned to the queue"), indicator: "green"});
					me.fetch_queue();
					me.open_document(document.name);
				})
				.catch((error) => frappe.msgprint(utils.server_message(error)));
		});
	},

	candidate_html(row) {
		const utils = dispatch_portal.utils;
		const readonly = !row.can_write_trip;
		const checked = row.can_write_trip && row.differs ? "checked" : "";

		return `<div class="al-dispatch-candidate ${readonly ? "readonly" : ""}">
			<input type="checkbox" data-candidate="${utils.escape(row.extracted_field)}" value="${utils.escape(
			row.trip_field || ""
		)}" ${checked} ${readonly ? "disabled" : ""} />
			<span class="al-dispatch-candidate-label">${utils.escape(row.label)}</span>
			<span class="al-dispatch-candidate-value">
				<strong>${utils.escape(String(row.extracted_value))}</strong>
				${readonly ? `<em class="al-dispatch-muted"> (${__("reference only")})</em>` : ""}
			</span>
			<span class="al-dispatch-candidate-current">
				${
					row.can_write_trip
						? `${__("Current trip value")}: <span class="${
								row.differs ? "differs" : ""
						  }">${utils.escape(String(row.current_value === null ? "-" : row.current_value))}</span>`
						: `<span class="al-dispatch-muted">${__("Not written to the trip")}</span>`
				}
			</span>
		</div>`;
	},

	apply_review(document) {
		const utils = dispatch_portal.utils;
		const me = this;
		const accepted = [];
		this.$detail.find("input[data-candidate]:checked").each(function () {
			accepted.push({extracted_field: $(this).attr("data-candidate")});
		});

		if (!accepted.length) {
			frappe.msgprint(__("Select at least one verified value to apply."));
			return;
		}

		frappe
			.call({
				method: "dispatch_portal.api.verification.apply_extraction_values",
				args: {document_name: document.name, accepted_fields: accepted},
				btn: this.$detail.find("[data-apply-review]"),
			})
			.then((response) => {
				const result = response.message || {};
				frappe.show_alert({
					message: __("Applied {0} value(s) to {1}", [
						(result.applied_fields || []).length,
						document.transport_trip,
					]),
					indicator: "green",
				});
				me.fetch_queue();
				me.open_document(document.name);
			})
			.catch((error) => frappe.msgprint(utils.server_message(error) || __("Verification failed.")));
	},

	reject_review(document) {
		const utils = dispatch_portal.utils;
		const me = this;
		const dialog = new frappe.ui.Dialog({
			title: __("Reject Document"),
			fields: [
				{
					label: __("Reason"),
					fieldname: "review_notes",
					fieldtype: "Small Text",
					reqd: 1,
				},
			],
			primary_action_label: __("Reject"),
			primary_action: (values) => {
				frappe
					.call({
						method: "dispatch_portal.api.verification.reject_document_review",
						args: {document_name: document.name, review_notes: values.review_notes},
						btn: dialog.get_primary_btn(),
					})
					.then(() => {
						dialog.hide();
						frappe.show_alert({message: __("Document rejected"), indicator: "orange"});
						me.fetch_queue();
						me.open_document(document.name);
					})
					.catch((error) => frappe.msgprint(utils.server_message(error)));
			},
		});
		dialog.show();
	},
};
