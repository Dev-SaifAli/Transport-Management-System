"""Role and permission setup for Transport Management users."""

from __future__ import annotations

import frappe
from frappe.modules import reload_doc


ROLE_TMS_TRIP_DATA_ENTRY = "TMS Trip Data Entry"
ROLE_TMS_EXPENSE_DATA_ENTRY = "TMS + Expense Data Entry"
ROLE_TRANSPORT_MANAGER = "Transport Manager"
ROLE_TRANSPORT_ADMIN = "Transport Admin"

TMS_ROLES = (
	ROLE_TMS_TRIP_DATA_ENTRY,
	ROLE_TMS_EXPENSE_DATA_ENTRY,
	ROLE_TRANSPORT_MANAGER,
	ROLE_TRANSPORT_ADMIN,
)

ROLE_PROFILES = {
	"TMS Trip Data Entry": (ROLE_TMS_TRIP_DATA_ENTRY,),
	"TMS + Expense Data Entry": (ROLE_TMS_TRIP_DATA_ENTRY, ROLE_TMS_EXPENSE_DATA_ENTRY),
	"Transport Manager": (ROLE_TRANSPORT_MANAGER,),
	"Transport Admin": (ROLE_TRANSPORT_ADMIN,),
}

READ_ONLY = {
	"read": 1,
	"report": 1,
	"export": 1,
	"print": 1,
	"email": 1,
}

ENTRY_DRAFT = {
	"read": 1,
	"write": 1,
	"create": 1,
	"report": 1,
	"export": 1,
	"print": 1,
	"email": 1,
}

MANAGE = {
	"read": 1,
	"write": 1,
	"create": 1,
	"report": 1,
	"export": 1,
	"import": 1,
	"print": 1,
	"email": 1,
	"share": 1,
}

MANAGE_SUBMIT = {
	**MANAGE,
	"submit": 1,
}

ADMIN = {
	**MANAGE_SUBMIT,
	"delete": 1,
	"cancel": 1,
	"amend": 1,
}

STANDARD_DOCTYPE_PERMISSIONS = {
	"Customer": {
		ROLE_TMS_TRIP_DATA_ENTRY: READ_ONLY,
		ROLE_TRANSPORT_MANAGER: MANAGE,
		ROLE_TRANSPORT_ADMIN: ADMIN,
	},
	"Supplier": {
		ROLE_TMS_TRIP_DATA_ENTRY: READ_ONLY,
		ROLE_TRANSPORT_MANAGER: MANAGE,
		ROLE_TRANSPORT_ADMIN: ADMIN,
	},
	"Employee": {
		ROLE_TRANSPORT_MANAGER: READ_ONLY,
		ROLE_TRANSPORT_ADMIN: MANAGE,
	},
	"Purchase Invoice": {
		ROLE_TMS_EXPENSE_DATA_ENTRY: ENTRY_DRAFT,
		ROLE_TRANSPORT_MANAGER: MANAGE_SUBMIT,
		ROLE_TRANSPORT_ADMIN: ADMIN,
	},
	"Purchase Order": {
		ROLE_TRANSPORT_MANAGER: MANAGE_SUBMIT,
		ROLE_TRANSPORT_ADMIN: ADMIN,
	},
	"Sales Invoice": {
		ROLE_TRANSPORT_MANAGER: MANAGE_SUBMIT,
		ROLE_TRANSPORT_ADMIN: ADMIN,
	},
	"Sales Order": {
		ROLE_TRANSPORT_MANAGER: MANAGE_SUBMIT,
		ROLE_TRANSPORT_ADMIN: ADMIN,
	},
}

TMS_PERMISSION_DOCTYPES = (
	"cargo_types",
	"hired_vehicle",
	"tms_import_log",
	"transport_rate",
	"transport_job",
	"transport_location",
	"transport_sales_order_item",
	"transport_sales_order",
	"transport_trip",
	"truck",
	"truck_driver",
	"truck_type",
)

PERMISSION_FIELDS = (
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
)


def ensure_tms_rbac():
	"""Create/update TMS roles, role profiles, and standard DocType permissions."""
	ensure_roles()
	ensure_role_profiles()
	sync_tms_doctype_permissions()
	ensure_standard_doctype_permissions()
	frappe.clear_cache()
	return "TMS RBAC configured"


def ensure_roles():
	for role in TMS_ROLES:
		if frappe.db.exists("Role", role):
			continue
		doc = frappe.new_doc("Role")
		doc.role_name = role
		doc.desk_access = 1
		doc.insert(ignore_permissions=True)


def ensure_role_profiles():
	for profile_name, roles in ROLE_PROFILES.items():
		if frappe.db.exists("Role Profile", profile_name):
			doc = frappe.get_doc("Role Profile", profile_name)
			doc.roles = []
		else:
			doc = frappe.new_doc("Role Profile")
			doc.role_profile = profile_name

		for role in roles:
			doc.append("roles", {"role": role})

		doc.save(ignore_permissions=True)


def sync_tms_doctype_permissions():
	for doctype in TMS_PERMISSION_DOCTYPES:
		reload_doc("transport_management", "doctype", doctype, force=True)


def ensure_standard_doctype_permissions():
	for doctype, role_permissions in STANDARD_DOCTYPE_PERMISSIONS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		for role, permissions in role_permissions.items():
			upsert_custom_docperm(doctype, role, permissions)
		frappe.clear_cache(doctype=doctype)


def upsert_custom_docperm(doctype, role, permissions):
	values = build_permission_row(doctype, role, permissions)
	existing = frappe.db.get_value(
		"Custom DocPerm",
		{
			"parent": doctype,
			"role": role,
			"permlevel": 0,
			"if_owner": 0,
		},
		"name",
	)

	if existing:
		doc = frappe.get_doc("Custom DocPerm", existing)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return doc

	doc = frappe.new_doc("Custom DocPerm")
	doc.update(values)
	doc.insert(ignore_permissions=True)
	return doc


def build_permission_row(doctype, role, permissions):
	row = {
		"parent": doctype,
		"role": role,
		"permlevel": 0,
		"if_owner": 0,
	}
	for fieldname in PERMISSION_FIELDS:
		row[fieldname] = 1 if permissions.get(fieldname) else 0
	return row
