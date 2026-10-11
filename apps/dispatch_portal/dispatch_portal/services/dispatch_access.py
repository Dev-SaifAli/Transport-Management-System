"""Dispatcher-specific access control for AL RANA Dispatch.

The console never re-implements transportation business rules.  Everything here
is *authorization* only: who may open the console, who may verify documents and
which TMS DocTypes the caller may still read/write.  The actual domain rules stay
in ``transport_management`` and are enforced by Frappe's own permission layer.
"""

from __future__ import annotations

import frappe
from frappe import _

APP_NAME = "dispatch_portal"
APP_TITLE = "AL RANA Dispatch"
DISPATCH_CONSOLE_ROUTE = "/app/dispatch-console"

ROLE_DISPATCHER = "AL RANA Dispatcher"
ROLE_VERIFIER = "AL RANA Dispatch Verifier"

DISPATCH_ROLES = (ROLE_DISPATCHER, ROLE_VERIFIER)
DISPATCH_ROLE_PROFILE = ROLE_DISPATCHER

# Console read access.  Existing AL RANA TMS roles keep working out of the box so
# the console is usable on day one, while the dedicated dispatch roles allow the
# least-privilege setup for users who should only ever see the console.
CONSOLE_READ_ROLES = frozenset(
	{
		ROLE_DISPATCHER,
		ROLE_VERIFIER,
		"System Manager",
		"Transport Admin",
		"Transport Manager",
		"TMS + Expense Data Entry",
		"TMS Trip Data Entry",
	}
)

# Document verification / AI extraction approval.  Deliberately narrower than the
# console read roles: approving an extraction writes authoritative trip data.
VERIFICATION_ROLES = frozenset(
	{
		ROLE_VERIFIER,
		"System Manager",
		"Transport Admin",
		"Transport Manager",
	}
)

TRIP_READ_DOCTYPES = ("Transport Trip", "Transport Job")
DISPATCH_DOCTYPES = (
	"Transport Trip",
	"Transport Job",
	"Transport Sales Order",
	"Transport Location",
	"Transport Trip Document",
	"Cargo Types",
	"Truck",
	"Truck Driver",
	"Hired Vehicle",
)

INACTIVE_USERS = ("Guest",)


class DispatchAccessError(frappe.PermissionError):
	"""Raised when a dispatcher action is not authorised (HTTP 403)."""


def is_dispatch_user(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not user or user in INACTIVE_USERS:
		return False
	return has_common_role(user, CONSOLE_READ_ROLES)


def is_verifier(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if not user or user in INACTIVE_USERS:
		return False
	return has_common_role(user, VERIFICATION_ROLES)


def has_common_role(user: str, roles) -> bool:
	allowed = frozenset(roles)
	if not allowed:
		return False
	if user == "Administrator":
		return True
	if not frappe.db.exists("User", user):
		return False
	return bool(allowed.intersection(frappe.get_roles(user)))


def get_user_roles(user: str | None = None) -> list[str]:
	user = user or frappe.session.user
	if not user or user in INACTIVE_USERS:
		return []
	if user == "Administrator":
		return sorted(CONSOLE_READ_ROLES)
	if not frappe.db.exists("User", user):
		return []
	return list(frappe.get_roles(user))


def require_console_access() -> None:
	if is_dispatch_user():
		return
	frappe.throw(
		_("You do not have access to the AL RANA Dispatch console."),
		exc=DispatchAccessError,
	)


def require_verification_access() -> None:
	require_console_access()
	if is_verifier():
		return
	frappe.throw(
		_("You are not authorised to verify transport trip documents."),
		exc=DispatchAccessError,
	)


def require_doctype_read(doctype: str) -> None:
	require_console_access()
	if doctype not in DISPATCH_DOCTYPES:
		frappe.throw(
			_("{0} is not a DocType exposed by the dispatcher console.").format(doctype),
			exc=frappe.ValidationError,
		)
	if not frappe.has_permission(doctype, ptype="read"):
		frappe.throw(
			_("You do not have permission to read {0}.").format(doctype),
			exc=DispatchAccessError,
		)


def get_dispatch_roles_for_user(user: str | None = None) -> dict:
	"""Role flags the console uses to enable or hide dispatcher capabilities."""
	user = user or frappe.session.user
	roles = set(get_user_roles(user))
	return {
		"user": user,
		"full_name": frappe.utils.get_fullname(user) if user not in INACTIVE_USERS else None,
		"is_dispatcher": is_dispatch_user(user),
		"is_verifier": is_verifier(user),
		"can_read_transport_trip": _has_doc_permission(user, "Transport Trip"),
		"can_read_transport_job": _has_doc_permission(user, "Transport Job"),
		"can_write_transport_trip": _has_doc_permission(user, "Transport Trip", "write"),
		"can_create_transport_trip": _has_doc_permission(user, "Transport Trip", "create"),
		"can_read_transport_trip_document": _has_doc_permission(
			user, "Transport Trip Document"
		),
		"can_write_transport_trip_document": _has_doc_permission(
			user, "Transport Trip Document", "write"
		),
		"can_read_truck": _has_doc_permission(user, "Truck"),
		"can_read_truck_driver": _has_doc_permission(user, "Truck Driver"),
		"roles": sorted(roles),
	}


def _has_doc_permission(user: str, doctype: str, ptype: str = "read") -> bool:
	if user in INACTIVE_USERS:
		return False
	return bool(frappe.has_permission(doctype, ptype=ptype, user=user))


def ensure_dispatch_roles() -> None:
	"""Create the dispatch roles and the dispatcher role profile (idempotent)."""
	for role in DISPATCH_ROLES:
		if frappe.db.exists("Role", role):
			continue
		doc = frappe.new_doc("Role")
		doc.role_name = role
		doc.desk_access = 1
		doc.insert(ignore_permissions=True)

	if frappe.db.exists("Role Profile", DISPATCH_ROLE_PROFILE):
		profile = frappe.get_doc("Role Profile", DISPATCH_ROLE_PROFILE)
		profile.roles = []
	else:
		profile = frappe.new_doc("Role Profile")
		profile.role_profile = DISPATCH_ROLE_PROFILE

	profile.append("roles", {"role": ROLE_DISPATCHER})
	profile.save(ignore_permissions=True)

	frappe.clear_cache()
