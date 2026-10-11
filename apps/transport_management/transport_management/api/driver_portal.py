"""Whitelisted Driver Portal authentication endpoints."""

import frappe

from transport_management.services.driver_portal_auth import (
	get_current_driver,
	logout_current_session,
	request_driver_otp,
	verify_driver_otp,
)
from transport_management.services.driver_portal_documents import get_trip_documents as get_documents_for_trip
from transport_management.services.driver_portal_documents import upload_trip_document as upload_document_for_trip
from transport_management.services.driver_portal_trips import get_my_trips as get_my_trips_for_driver
from transport_management.services.driver_portal_trips import get_trip_detail
from transport_management.services.driver_portal_trips import mark_driver_trip_delivered
from transport_management.services.driver_portal_trips import start_driver_trip


@frappe.whitelist(allow_guest=True, methods=["POST"])
def request_otp(mobile=None):
	"""Request a one-time password for a registered driver mobile number."""
	return request_driver_otp(mobile)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def verify_otp(mobile=None, otp=None):
	"""Verify a driver OTP and establish a Driver Portal session."""
	return verify_driver_otp(mobile, otp)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_me(**kwargs):
	"""Return the authenticated Driver Portal identity.

	Any caller-supplied driver_id is ignored. Identity is derived only from the
	Driver Portal token in the HttpOnly cookie or Authorization bearer header.
	"""
	return get_current_driver()


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_my_trips(view=None, status_group=None, limit=20, offset=0, **kwargs):
	"""Return Transport Trips for the authenticated Driver Portal driver only."""
	return get_my_trips_for_driver(view=view or status_group, limit=limit, offset=offset)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_trip(trip_id=None, **kwargs):
	"""Return one portal-safe Transport Trip detail for the authenticated driver."""
	return get_trip_detail(trip_id=trip_id)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def start_trip(trip_id=None, **kwargs):
	"""Start an assigned trip for the authenticated Driver Portal driver."""
	return start_driver_trip(trip_id=trip_id)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def mark_delivered(trip_id=None, **kwargs):
	"""Mark an in-transit trip delivered for the authenticated Driver Portal driver."""
	return mark_driver_trip_delivered(trip_id=trip_id)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def upload_trip_document(trip_id=None, document_type=None, file=None, **kwargs):
	"""Upload one trip evidence document for the authenticated driver."""
	return upload_document_for_trip(trip_id=trip_id, document_type=document_type, file=file)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_trip_documents(trip_id=None, **kwargs):
	"""Return portal-safe trip documents for the authenticated driver."""
	return get_documents_for_trip(trip_id=trip_id)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def logout():
	"""Revoke the current Driver Portal session."""
	return logout_current_session()
