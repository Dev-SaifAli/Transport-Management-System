"""Reconcile AL RANA Desk metadata with the DocType JSON source of truth.

Two localhost-only customizations used to live purely in the database and were
therefore lost on a fresh installation:

1. The Transport Job list view columns.
2. The "TRN Number" label on ``Company.tax_id``.

Both are handled here so they can be recreated on any environment from source
control, without touching business records.

Ordering note: this is a ``post_model_sync`` patch, so the DocType JSON has
already been synced into the database when it runs. The JSON is authoritative.

Transaction note: no ``frappe.db.commit()`` is issued here. The patch runner
commits once after a successful patch and rolls the whole patch back if it
raises, so a partial failure can never leave half of the change behind, and an
enclosing test savepoint stays intact.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


TRANSPORT_JOB = "Transport Job"

# Field names whose list-view visibility the JSON controls. Localhost used to
# override some of them with point-and-click Property Setters; the full set is
# listed so any future override on these fields is also reconciled. Removal is
# conditional on a setter existing, so listing a field with no setter is a
# no-op.
TRANSPORT_JOB_LIST_VIEW_FIELDS = (
	"billing_status",
	"customer",
	"delivered_quantity",
	"loading_site",
	"material",
	"remaining_quantity",
	"requested_quantity",
	"sale_order_reference",
	"status",
	"toll_billing_status",
	"unloading_site",
)

COMPANY = "Company"
COMPANY_TAX_ID_FIELD = "tax_id"
COMPANY_TAX_ID_LABEL = "TRN Number"


def execute():
	reconcile_transport_job_list_view()
	ensure_company_tax_id_label()
	frappe.clear_cache(doctype=TRANSPORT_JOB)
	frappe.clear_cache(doctype=COMPANY)
	return "AL RANA desk metadata reconciled with source"


def reconcile_transport_job_list_view():
	"""Drop list-view Property Setters for Transport Job.

	These were created by point-and-click customization and now only duplicate
	or contradict ``transport_job.json``. Because the JSON is synced before
	post_model_sync patches run, removing them yields exactly the column layout
	the JSON declares, so the rendered list view is unchanged on localhost and
	becomes reproducible everywhere else.

	Only setters that exist are removed, and only for the known field names
	above, so running the patch repeatedly is a no-op.
	"""
	if not frappe.db.exists("DocType", TRANSPORT_JOB):
		return

	for fieldname in TRANSPORT_JOB_LIST_VIEW_FIELDS:
		name = frappe.db.get_value(
			"Property Setter",
			{
				"doc_type": TRANSPORT_JOB,
				"field_name": fieldname,
				"property": "in_list_view",
			},
			"name",
		)
		if name:
			frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)


def ensure_company_tax_id_label():
	"""Recreate the "TRN Number" label for ``Company.tax_id``.

	``make_property_setter`` deletes any pre-existing matching setter before
	inserting, which makes this idempotent. The label is marked
	system-generated so it is treated as app-owned metadata rather than an
	ad-hoc UI customization. Only the label changes; the tax identification
	values stored on Company records are never written to.
	"""
	if not frappe.db.exists("DocField", {"parent": COMPANY, "fieldname": COMPANY_TAX_ID_FIELD}):
		return

	existing = frappe.db.get_value(
		"Property Setter",
		{
			"doc_type": COMPANY,
			"field_name": COMPANY_TAX_ID_FIELD,
			"property": "label",
		},
		"name",
	)
	if existing:
		frappe.db.set_value(
			"Property Setter",
			existing,
			{
				"value": COMPANY_TAX_ID_LABEL,
				"property_type": "Data",
				"is_system_generated": 1,
			},
			update_modified=False,
		)
		return

	make_property_setter(
		COMPANY,
		COMPANY_TAX_ID_FIELD,
		"label",
		COMPANY_TAX_ID_LABEL,
		"Data",
		is_system_generated=True,
	)
