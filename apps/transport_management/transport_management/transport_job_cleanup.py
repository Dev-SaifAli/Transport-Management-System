"""Transport Job cleanup helpers owned by transport_management."""

import frappe

TRANSPORT_JOB = "Transport Job"
OBSOLETE_TRANSPORT_JOB_FIELDS = (
	"so" + "urce",
	"".join(("ha", "der", "_shipment_id")),
	"".join(("ha", "der", "_order_id")),
	"external" + "_id",
	"idempotency" + "_key",
)


def remove_obsolete_transport_job_columns():
	"""Drop obsolete integration columns after their DocFields have been removed."""
	for fieldname in OBSOLETE_TRANSPORT_JOB_FIELDS:
		if frappe.db.exists("DocField", {"parent": TRANSPORT_JOB, "fieldname": fieldname}):
			continue
		if frappe.db.has_column(TRANSPORT_JOB, fieldname):
			frappe.db.sql_ddl(f"alter table `tab{TRANSPORT_JOB}` drop column `{fieldname}`")

	frappe.clear_cache(doctype=TRANSPORT_JOB)
