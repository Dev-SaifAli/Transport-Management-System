"""Driver Portal operational notifications.

Trip assignment notification is intentionally separate from OTP auth. Providers
can be configured later through the ``driver_portal_notification_sender`` hook.
"""

from __future__ import annotations

import re

import frappe
from frappe.utils import cint, escape_html, now_datetime

from transport_management.services.driver_portal_auth import AL_RANA_COMPANY, is_developer_mode

ASSIGNMENT_NOTIFICATION_TYPE = "TRIP_ASSIGNED"
DEVELOPMENT_NOTIFICATION_CACHE_KEY = "tms_driver_portal:development_notifications"
NOTIFICATION_STATUSES = {"NOT_SENT", "SENT", "FAILED", "SKIPPED"}


def queue_driver_trip_assignment_notification(trip_name: str, previous_driver: str | None = None) -> None:
	frappe.enqueue(
		"transport_management.services.driver_notifications.notify_driver_trip_assignment",
		queue="short",
		enqueue_after_commit=True,
		trip_name=trip_name,
		previous_driver=previous_driver,
	)


def notify_driver_trip_assignment(trip_name: str, previous_driver: str | None = None) -> dict:
	trip = frappe.db.get_value(
		"Transport Trip",
		trip_name,
		["name", "driver", "loading_site", "unloading_site"],
		as_dict=True,
	)
	if not trip:
		return {"ok": False, "status": "SKIPPED", "reason": "Trip not found."}

	if not trip.driver:
		return record_assignment_notification_status(
			trip.name,
			"SKIPPED",
			"Driver was removed before notification could be sent.",
			driver=None,
			mobile=None,
		)

	driver = get_driver_for_notification(trip.driver)
	if not driver.ok:
		return record_assignment_notification_status(
			trip.name,
			"SKIPPED",
			driver.error,
			driver=trip.driver,
			mobile=driver.get("mobile"),
		)

	message = build_trip_assignment_message(trip)
	if not is_developer_mode() and is_dummy_mobile(driver.mobile):
		return record_assignment_notification_status(
			trip.name,
			"SKIPPED",
			"Dummy/test mobile number skipped in production.",
			driver=trip.driver,
			mobile=driver.mobile,
		)

	try:
		send_driver_notification(
			driver.mobile,
			message,
			notification_type=ASSIGNMENT_NOTIFICATION_TYPE,
			trip=trip.name,
			driver=trip.driver,
		)
	except Exception as exc:
		error = sanitize_error(exc)
		frappe.log_error(
			title="Driver trip assignment notification failed",
			message=f"Trip: {trip.name}\nDriver: {trip.driver}\nMobile: {mask_mobile(driver.mobile)}\nError: {error}",
		)
		return record_assignment_notification_status(
			trip.name,
			"FAILED",
			error,
			driver=trip.driver,
			mobile=driver.mobile,
		)

	return record_assignment_notification_status(
		trip.name,
		"SENT",
		"",
		driver=trip.driver,
		mobile=driver.mobile,
	)


def send_driver_notification(
	mobile: str,
	message: str,
	notification_type: str = ASSIGNMENT_NOTIFICATION_TYPE,
	**context,
) -> None:
	if is_developer_mode():
		capture_development_notification(mobile, message, notification_type, context)
		return

	if is_dummy_mobile(mobile):
		raise DummyMobileSkippedError("Dummy/test mobile number skipped in production.")

	senders = frappe.get_hooks("driver_portal_notification_sender") or []
	if not senders:
		raise RuntimeError("Driver Portal notification provider is not configured.")

	for sender in senders:
		frappe.get_attr(sender)(
			mobile=mobile,
			message=message,
			notification_type=notification_type,
			context=context,
		)


def get_driver_for_notification(driver_name: str) -> frappe._dict:
	driver = frappe.db.get_value(
		"Truck Driver",
		driver_name,
		["name", "full_name", "cell_number", "employee", "status"],
		as_dict=True,
	)
	if not driver:
		return frappe._dict(ok=False, error="Truck Driver not found.")
	if driver.status != "Active":
		return frappe._dict(ok=False, error="Truck Driver is not active.", mobile=driver.cell_number)
	if not driver.cell_number:
		return frappe._dict(ok=False, error="Truck Driver mobile number is missing.")
	if not driver.employee:
		return frappe._dict(ok=False, error="Truck Driver is not linked to an Employee.", mobile=driver.cell_number)

	employee = frappe.db.get_value(
		"Employee",
		driver.employee,
		["name", "status", "company"],
		as_dict=True,
	)
	if not employee:
		return frappe._dict(ok=False, error="Linked Employee was not found.", mobile=driver.cell_number)
	if employee.status != "Active":
		return frappe._dict(ok=False, error="Linked Employee is not active.", mobile=driver.cell_number)
	if employee.company != AL_RANA_COMPANY:
		return frappe._dict(ok=False, error="Linked Employee is not part of AL RANA TRANSPORT LLC.", mobile=driver.cell_number)

	return frappe._dict(ok=True, mobile=driver.cell_number, driver=driver.name)


def build_trip_assignment_message(trip: frappe._dict) -> str:
	loading = get_location_label(trip.loading_site)
	unloading = get_location_label(trip.unloading_site)
	return "\n".join(
		[
			"AL RANA: New trip assigned.",
			f"Trip: {trip.name}",
			f"Route: {loading} -> {unloading}",
			"Please open the Driver Portal to review your trip.",
		]
	)


def get_location_label(location: str | None) -> str:
	if not location:
		return "-"
	return frappe.db.get_value("Transport Location", location, "location") or location


def record_assignment_notification_status(
	trip_name: str,
	status: str,
	error: str = "",
	driver: str | None = None,
	mobile: str | None = None,
) -> dict:
	if status not in NOTIFICATION_STATUSES:
		status = "FAILED"

	values = {}
	if has_trip_column("assignment_notification_status"):
		values["assignment_notification_status"] = status
	if has_trip_column("assignment_notification_error"):
		values["assignment_notification_error"] = error[:1000] if error else ""
	if has_trip_column("assignment_notified_at"):
		values["assignment_notified_at"] = now_datetime() if status == "SENT" else None

	if values:
		frappe.db.set_value("Transport Trip", trip_name, values, update_modified=False)

	add_assignment_notification_comment(trip_name, status, error, driver, mobile)
	return {"ok": status == "SENT", "status": status, "error": error}


def add_assignment_notification_comment(
	trip_name: str,
	status: str,
	error: str = "",
	driver: str | None = None,
	mobile: str | None = None,
) -> None:
	try:
		trip = frappe.get_doc("Transport Trip", trip_name)
		message = (
			f"DRIVER_ASSIGNMENT_NOTIFIED<br>Status: {status}<br>"
			f"Driver: {driver or '-'}<br>Mobile: {mask_mobile(mobile) if mobile else '-'}"
		)
		if error:
			message += f"<br>Error: {escape_html(error[:500])}"
		trip.add_comment("Info", message)
	except Exception:
		# Audit comments are helpful but must not break operational saves/jobs.
		pass


def capture_development_notification(
	mobile: str,
	message: str,
	notification_type: str,
	context: dict | None = None,
) -> None:
	payload = {
		"mobile": mobile,
		"masked_mobile": mask_mobile(mobile),
		"message": message,
		"notification_type": notification_type,
		"context": context or {},
		"created_at": now_datetime().isoformat(),
	}
	notifications = get_development_notifications()
	notifications.append(payload)
	frappe.cache.set_value(DEVELOPMENT_NOTIFICATION_CACHE_KEY, notifications, expires_in_sec=60 * 60)


def get_development_notifications() -> list[dict]:
	return frappe.cache.get_value(DEVELOPMENT_NOTIFICATION_CACHE_KEY, expires=True) or []


def clear_development_notifications() -> None:
	frappe.cache.delete_value(DEVELOPMENT_NOTIFICATION_CACHE_KEY)


def is_dummy_mobile(mobile: str | None) -> bool:
	return bool(mobile and re.fullmatch(r"05000000\d{2}", str(mobile).strip()))


def mask_mobile(mobile: str | None) -> str:
	if not mobile:
		return ""
	mobile = str(mobile)
	if len(mobile) <= 4:
		return "****"
	return f"{mobile[:2]}****{mobile[-2:]}"


def sanitize_error(exc: Exception) -> str:
	return str(exc).replace("\n", " ")[:1000] or exc.__class__.__name__


def has_trip_column(fieldname: str) -> bool:
	return bool(cint(frappe.db.has_column("Transport Trip", fieldname)))


class DummyMobileSkippedError(RuntimeError):
	pass
