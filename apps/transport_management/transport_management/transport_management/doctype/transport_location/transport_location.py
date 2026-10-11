# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

import math

import requests

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

DEFAULT_COUNTRY = "United Arab Emirates"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_USER_AGENT = "transport_management/1.0 (Frappe TMS development geocoding)"


class TransportLocation(Document):
	def before_validate(self):
		if self.active is None:
			self.active = 1
		if not self.country:
			self.country = DEFAULT_COUNTRY

	def validate(self):
		validate_coordinates(self.latitude, self.longitude)


def validate_coordinates(latitude=None, longitude=None):
	if latitude not in (None, ""):
		latitude = parse_coordinate(latitude, "Latitude")
		if latitude < -90 or latitude > 90:
			frappe.throw(_("Latitude must be between -90 and 90."))
	if longitude not in (None, ""):
		longitude = parse_coordinate(longitude, "Longitude")
		if longitude < -180 or longitude > 180:
			frappe.throw(_("Longitude must be between -180 and 180."))


def parse_coordinate(value, label):
	try:
		coordinate = float(value)
	except (TypeError, ValueError):
		frappe.throw(_("{0} must be a valid number.").format(_(label)))
	if not math.isfinite(coordinate):
		frappe.throw(_("{0} must be a valid number.").format(_(label)))
	return coordinate


@frappe.whitelist()
def search_location(query, country=None, limit=5):
	query = (query or "").strip()
	if not query:
		return []
	try:
		limit = min(max(int(limit or 5), 1), 10)
	except Exception:
		limit = 5
	country = country or DEFAULT_COUNTRY
	params = {
		"q": f"{query} {country}" if country and country.lower() not in query.lower() else query,
		"format": "jsonv2",
		"addressdetails": 1,
		"limit": limit,
	}
	try:
		response = requests.get(
			f"{NOMINATIM_URL}/search",
			params=params,
			headers={"User-Agent": NOMINATIM_USER_AGENT},
			timeout=8,
		)
		response.raise_for_status()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Transport Location search failed")
		frappe.throw(_("Location search is temporarily unavailable. You can still select the location manually on the map."))

	return [normalize_nominatim_result(row) for row in response.json()]


@frappe.whitelist()
def reverse_geocode(latitude, longitude):
	validate_coordinates(latitude, longitude)
	params = {
		"lat": flt(latitude),
		"lon": flt(longitude),
		"format": "jsonv2",
		"addressdetails": 1,
	}
	try:
		response = requests.get(
			f"{NOMINATIM_URL}/reverse",
			params=params,
			headers={"User-Agent": NOMINATIM_USER_AGENT},
			timeout=8,
		)
		response.raise_for_status()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Transport Location reverse geocode failed")
		return {}
	return normalize_nominatim_result(response.json())


def normalize_nominatim_result(row):
	address = row.get("address") or {}
	return {
		"display_name": row.get("display_name"),
		"latitude": flt(row.get("lat"), 8),
		"longitude": flt(row.get("lon"), 8),
		"city": pick_first(address, ("city", "town", "municipality", "village")),
		"area_zone": pick_first(address, ("suburb", "district", "county", "state_district", "neighbourhood")),
		"country": address.get("country"),
	}


def pick_first(values, keys):
	for key in keys:
		if values.get(key):
			return values.get(key)
	return None
