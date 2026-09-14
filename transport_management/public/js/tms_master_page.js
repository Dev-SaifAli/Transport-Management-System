frappe.provide("transport_management");

transport_management.make_tms_master_page = function (wrapper, opts) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: opts.title,
		single_column: true,
	});

	const open_workspace = () => frappe.set_route("transport-management");
	const open_list = () => frappe.set_route("List", opts.doctype, "List");
	const create_new = () => frappe.new_doc(opts.doctype);

	$(page.body).empty().append(`
		<div class="tms-master-wrapper">
			<div class="tms-master-panel">
				<div class="text-muted small">${__("Uses {0}.", [opts.master_label])}</div>
				<div class="mt-2">${__(
					"Records are stored in the standard master. This page keeps Transport Management navigation visible without duplicating data."
				)}</div>
				<div class="mt-4 tms-master-actions">
					<button class="btn btn-primary btn-sm" data-action="open-list">${opts.list_label}</button>
					<button class="btn btn-default btn-sm ml-2" data-action="create-new">${opts.new_label}</button>
					<button class="btn btn-default btn-sm ml-2" data-action="back-workspace">${__("Back to Transport Management")}</button>
				</div>
			</div>
		</div>
	`);

	const $body = $(page.body);
	$body.find('[data-action="back-workspace"]').on("click", open_workspace);

	frappe.model.with_doctype(opts.doctype, () => {
		if (frappe.model.can_read(opts.doctype)) {
			page.set_primary_action(opts.list_label, open_list, "list");
			$body.find('[data-action="open-list"]').on("click", open_list);
		} else {
			$body.find('[data-action="open-list"]').prop("disabled", true);
		}

		if (frappe.model.can_create(opts.doctype)) {
			page.add_action_item(opts.new_label, create_new);
			$body.find('[data-action="create-new"]').on("click", create_new);
		} else {
			$body.find('[data-action="create-new"]').prop("disabled", true);
		}

		page.add_action_item(__("Back to Transport Management"), open_workspace);
	});
};
