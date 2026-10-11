"""Driver Portal OTP and opaque-token authentication.

This module intentionally does not create Frappe ``User`` records. Driver
Portal identity is represented by a short-lived OTP challenge followed by an
opaque portal token stored hashed in Redis/cache. Future portal APIs should call
``get_current_driver`` or ``get_current_driver_from_token`` and must never trust
a driver id supplied by the frontend.
"""

from __future__ import annotations

import hmac
import re
import secrets
from datetime import timedelta
from hashlib import sha256

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

AL_RANA_COMPANY = "AL RANA TRANSPORT LLC"
COOKIE_NAME = "tms_driver_portal_token"
GENERIC_OTP_MESSAGE = "If this mobile is registered, an OTP has been sent."
OTP_EXPIRY_SECONDS = 5 * 60
OTP_LENGTH = 6
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_IP_WINDOW_SECONDS = 5 * 60
OTP_IP_MAX_REQUESTS = 20
SESSION_EXPIRY_SECONDS = 30 * 24 * 60 * 60


class DriverPortalAuthError(frappe.PermissionError):
	pass


def request_driver_otp(mobile: str | None) -> dict:
	normalized_mobile = normalize_mobile(mobile)
	ip_address = get_request_ip()
	response = {"ok": True, "message": GENERIC_OTP_MESSAGE}

	if not normalized_mobile:
		register_rate_limit_attempt("missing", ip_address)
		return response

	if not register_rate_limit_attempt(normalized_mobile, ip_address):
		return response

	identity = resolve_driver_identity(normalized_mobile)
	if not identity:
		return response

	otp = generate_otp()
	challenge = {
		"mobile": normalized_mobile,
		"otp_hash": hash_secret(f"otp:{normalized_mobile}:{otp}"),
		"expires_at": get_expiry_timestamp(OTP_EXPIRY_SECONDS),
		"attempt_count": 0,
		"used": False,
		"created_at": now_datetime().isoformat(),
		"request_ip": ip_address,
	}

	try:
		send_driver_otp(normalized_mobile, otp)
	except Exception:
		frappe.log_error(
			title="Driver Portal OTP delivery failed",
			message=frappe.get_traceback(with_context=True),
		)
		return response

	frappe.cache.set_value(
		get_otp_key(normalized_mobile),
		challenge,
		expires_in_sec=OTP_EXPIRY_SECONDS,
	)

	if is_developer_mode():
		# Local development only. Never expose OTPs in production responses/logs.
		response["debug_otp"] = otp

	return response


def verify_driver_otp(mobile: str | None, otp: str | None) -> dict:
	normalized_mobile = normalize_mobile(mobile)
	otp = normalize_otp(otp)

	if not normalized_mobile or not otp:
		raise_unauthorized(_("Invalid or expired OTP."))

	challenge_key = get_otp_key(normalized_mobile)
	challenge = frappe.cache.get_value(challenge_key, expires=True)
	if not challenge:
		raise_unauthorized(_("Invalid or expired OTP."))

	if challenge.get("used") or is_expired(challenge.get("expires_at")):
		frappe.cache.delete_value(challenge_key)
		raise_unauthorized(_("Invalid or expired OTP."))

	attempt_count = cint(challenge.get("attempt_count")) + 1
	challenge["attempt_count"] = attempt_count
	remaining_seconds = max(seconds_until(challenge.get("expires_at")), 1)
	frappe.cache.set_value(challenge_key, challenge, expires_in_sec=remaining_seconds)

	if attempt_count > OTP_MAX_ATTEMPTS:
		frappe.cache.delete_value(challenge_key)
		raise_unauthorized(_("Too many OTP attempts. Please request a new OTP."))

	expected_hash = challenge.get("otp_hash") or ""
	actual_hash = hash_secret(f"otp:{normalized_mobile}:{otp}")
	if not hmac.compare_digest(expected_hash, actual_hash):
		raise_unauthorized(_("Invalid or expired OTP."))

	identity = resolve_driver_identity(normalized_mobile)
	if not identity:
		frappe.cache.delete_value(challenge_key)
		raise_unauthorized(_("Invalid or expired OTP."))

	frappe.cache.delete_value(challenge_key)
	token = create_driver_session(identity, normalized_mobile)
	set_driver_cookie(token)

	return {
		"ok": True,
		"message": "OTP verified.",
		"token": token,
		"driver": get_portal_safe_driver(identity, normalized_mobile),
	}


def get_current_driver() -> dict:
	identity = require_current_driver_identity()
	return {"ok": True, "driver": get_portal_safe_driver(identity, identity.mobile)}


def require_current_driver_identity() -> frappe._dict:
	token = get_request_token()
	identity = get_current_driver_from_token(token)
	if not identity:
		raise_unauthorized(_("Driver Portal session is required."))
	return identity


def logout_current_session() -> dict:
	token = get_request_token()
	if token:
		revoke_driver_session(token)
	clear_driver_cookie()
	return {"ok": True, "message": "Logged out."}


def get_current_driver_from_token(token: str | None) -> frappe._dict | None:
	if not token:
		return None

	session = frappe.cache.get_value(get_session_key(token), expires=True)
	if not session:
		return None

	identity = resolve_driver_identity(session.get("mobile"))
	if not identity:
		revoke_driver_session(token)
		return None

	return identity


def create_driver_session(identity: frappe._dict, mobile: str) -> str:
	token = secrets.token_urlsafe(48)
	session = {
		"mobile": mobile,
		"truck_driver": identity.truck_driver,
		"employee": identity.employee,
		"created_at": now_datetime().isoformat(),
		"expires_at": get_expiry_timestamp(SESSION_EXPIRY_SECONDS),
		"request_ip": get_request_ip(),
	}
	frappe.cache.set_value(
		get_session_key(token),
		session,
		expires_in_sec=SESSION_EXPIRY_SECONDS,
	)
	return token


def revoke_driver_session(token: str) -> None:
	frappe.cache.delete_value(get_session_key(token))


def resolve_driver_identity(mobile: str | None) -> frappe._dict | None:
	if not mobile:
		return None

	drivers = frappe.get_all(
		"Truck Driver",
		filters={"cell_number": mobile},
		fields=["name", "full_name", "employee", "status", "cell_number"],
		limit=2,
	)
	if len(drivers) != 1:
		return None

	driver = drivers[0]
	if driver.status != "Active" or not driver.employee:
		return None

	employee = frappe.db.get_value(
		"Employee",
		driver.employee,
		["name", "employee_name", "status", "company"],
		as_dict=True,
	)
	if not employee:
		return None

	if employee.status != "Active" or employee.company != AL_RANA_COMPANY:
		return None

	return frappe._dict(
		truck_driver=driver.name,
		employee=employee.name,
		driver_name=driver.full_name or employee.employee_name,
		mobile=driver.cell_number,
	)


def get_portal_safe_driver(identity: frappe._dict, mobile: str) -> dict:
	return {
		"truck_driver": identity.truck_driver,
		"employee": identity.employee,
		"driver_name": identity.driver_name,
		"mobile": mobile,
	}


def send_driver_otp(mobile: str, otp: str) -> None:
	"""Send OTP through a configured provider.

	Production SMS is intentionally abstracted. Apps can register a dotted-path
	function in ``driver_portal_sms_sender`` hooks. In developer mode this is a
	no-op and the API response includes ``debug_otp`` for local testing.
	"""
	if is_developer_mode():
		return

	senders = frappe.get_hooks("driver_portal_sms_sender") or []
	if not senders:
		raise RuntimeError("Driver Portal SMS provider is not configured.")

	for sender in senders:
		frappe.get_attr(sender)(mobile=mobile, otp=otp)


def normalize_mobile(mobile: str | None) -> str | None:
	if mobile is None:
		return None

	digits = re.sub(r"\D", "", str(mobile))
	if not digits:
		return None

	if digits.startswith("00971"):
		digits = "0" + digits[5:]
	elif digits.startswith("971"):
		digits = "0" + digits[3:]
	elif len(digits) == 9 and digits.startswith("5"):
		digits = "0" + digits

	return digits


def normalize_otp(otp: str | None) -> str | None:
	if otp is None:
		return None
	otp = str(otp).strip()
	if not re.fullmatch(r"\d{6}", otp):
		return None
	return otp


def generate_otp() -> str:
	return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def hash_secret(value: str) -> str:
	key = frappe.conf.get("encryption_key") or frappe.local.conf.get("db_name")
	if not key:
		raise RuntimeError("Site encryption key or database name is required for Driver Portal auth.")
	return hmac.new(str(key).encode(), value.encode(), sha256).hexdigest()


def get_otp_key(mobile: str) -> str:
	return f"tms_driver_portal:otp:{hash_secret(mobile)}"


def get_session_key(token: str) -> str:
	return f"tms_driver_portal:session:{hash_secret(token)}"


def get_cooldown_key(mobile: str) -> str:
	return f"tms_driver_portal:otp_cooldown:{hash_secret(mobile)}"


def get_ip_rate_key(ip_address: str) -> str:
	return f"tms_driver_portal:otp_ip:{hash_secret(ip_address or 'unknown')}"


def register_rate_limit_attempt(mobile: str, ip_address: str) -> bool:
	if frappe.cache.get_value(get_cooldown_key(mobile), expires=True):
		return False

	frappe.cache.set_value(
		get_cooldown_key(mobile),
		1,
		expires_in_sec=OTP_RESEND_COOLDOWN_SECONDS,
	)

	ip_key = get_ip_rate_key(ip_address)
	ip_count = cint(frappe.cache.get_value(ip_key, expires=True)) + 1
	frappe.cache.set_value(ip_key, ip_count, expires_in_sec=OTP_IP_WINDOW_SECONDS)
	return ip_count <= OTP_IP_MAX_REQUESTS


def get_request_token() -> str | None:
	auth_header = get_request_header("Authorization", "") or ""
	parts = auth_header.split()
	if len(parts) == 2 and parts[0].lower() == "bearer":
		return parts[1]

	request = getattr(frappe.local, "request", None)
	if request:
		return request.cookies.get(COOKIE_NAME)

	return None


def set_driver_cookie(token: str) -> None:
	cookie_manager = getattr(frappe.local, "cookie_manager", None)
	if cookie_manager:
		cookie_manager.set_cookie(
			COOKIE_NAME,
			token,
			httponly=True,
			samesite="Lax",
			max_age=SESSION_EXPIRY_SECONDS,
		)


def clear_driver_cookie() -> None:
	cookie_manager = getattr(frappe.local, "cookie_manager", None)
	if cookie_manager:
		cookie_manager.delete_cookie(COOKIE_NAME)


def get_request_ip() -> str:
	return getattr(frappe.local, "request_ip", None) or get_request_header("X-Forwarded-For", "").split(",", 1)[0].strip() or "unknown"


def get_request_header(key: str, default: str = "") -> str:
	try:
		return frappe.get_request_header(key, default) or default
	except RuntimeError:
		return default


def is_developer_mode() -> bool:
	return bool(cint(frappe.conf.get("developer_mode")))


def is_expired(expires_at: str | None) -> bool:
	if not expires_at:
		return True
	return get_datetime(expires_at) <= now_datetime()


def seconds_until(expires_at: str | None) -> int:
	if not expires_at:
		return 0
	return int((get_datetime(expires_at) - now_datetime()).total_seconds())


def get_expiry_timestamp(seconds: int) -> str:
	return (now_datetime() + timedelta(seconds=seconds)).isoformat(sep=" ")


def raise_unauthorized(message: str) -> None:
	frappe.local.response["http_status_code"] = 401
	frappe.throw(message, DriverPortalAuthError)
