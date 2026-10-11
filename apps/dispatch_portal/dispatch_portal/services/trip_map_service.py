"""Trip Map data provider.

Coordinates come from the real ``Transport Location`` master data owned by
``transport_management``.  Trips are drawn as origin -> destination legs plus
their loading stops; no trip, location or fleet entity is duplicated.
"""

from __future__ import annotations

import frappe

from dispatch_portal.services.dispatch_access import require_console_access
from dispatch_portal.services.trip_console import (
	get_effective_driver,
	get_effective_vehicle,
	list_trips,
	normalize_limit,
	to_float,
)

STATUS_GROUPS = {
	"planned": ("PLANNED",),
	"assigned": ("ASSIGNED",),
	"loaded": ("LOADED",),
	"in_transit": ("IN_TRANSIT",),
	"delivered": ("DELIVERED", "POD_RECEIVED"),
	"exception": ("EXCEPTION",),
	"closed": ("CLOSED",),
	"cancelled": ("CANCELLED",),
}


def get_trip_map(filters=None) -> dict:
	"""Return geolocated trips plus unlocated ones for the Trip Map section."""
	require_console_access()

	trip_filters = frappe._dict(filters or {})
	limit = normalize_limit(trip_filters.get("limit"), default=300, maximum=500)
	status_group = (trip_filters.get("status_group") or "").strip()
	if status_group and status_group in STATUS_GROUPS:
		trip_filters.status = ["in", list(STATUS_GROUPS[status_group])]

	trips = list_trips(trip_filters, page_length=limit, order_by="trip_date desc")

	locations = get_location_coordinates(trips)
	markers = []
	located_trips = 0
	for trip in trips:
		coords = resolve_trip_coordinates(trip, locations)
		if not coords:
			continue
		located_trips += 1
		markers.append(
			{
				"trip": trip.name,
				"status": trip.status,
				"trip_date": str(trip.get("trip_date") or ""),
				"route": build_route(trip.get("loading_site"), trip.get("unloading_site")),
				"vehicle": get_effective_vehicle(trip),
				"driver": get_effective_driver(trip),
				"origin": coords["origin"],
				"destination": coords["destination"],
				"stops": coords["stops"],
				"execution_source": trip.get("execution_source"),
			}
		)

	return {
		"total_trips": len(trips),
		"located_trips": located_trips,
		"unlocated_trips": len(trips) - located_trips,
		"markers": markers,
		"legend": [
			{"status": "PLANNED", "label": "Planned"},
			{"status": "ASSIGNED", "label": "Assigned"},
			{"status": "LOADED", "label": "Loaded"},
			{"status": "IN_TRANSIT", "label": "In Transit"},
			{"status": "DELIVERED", "label": "Delivered"},
			{"status": "EXCEPTION", "label": "Exception"},
			{"status": "CLOSED", "label": "Closed"},
			{"status": "CANCELLED", "label": "Cancelled"},
		],
	}


def resolve_trip_coordinates(trip, locations) -> dict | None:
	origin = locations.get(trip.get("loading_site"))
	destination = locations.get(trip.get("unloading_site"))
	stops = [
		locations.get(row.get("loading_location"))
		for row in trip.get("loading_stops") or []
	]
	stops = [stop for stop in stops if stop]

	legs = [leg for leg in (origin, destination) if leg]
	if not legs and not stops:
		return None

	return {
		"origin": origin,
		"destination": destination,
		"stops": stops,
	}


def get_location_coordinates(trips) -> dict:
	location_names = set()
	for trip in trips:
		if trip.get("loading_site"):
			location_names.add(trip.get("loading_site"))
		if trip.get("unloading_site"):
			location_names.add(trip.get("unloading_site"))
		for row in trip.get("loading_stops") or []:
			if row.get("loading_location"):
				location_names.add(row.get("loading_location"))

	if not location_names:
		return {}

	rows = frappe.get_all(
		"Transport Location",
		filters={"name": ["in", list(location_names)]},
		fields=["name", "location", "latitude", "longitude", "city", "location_type"],
		limit_page_length=max(len(location_names), 1),
	)
	return {row.name: serialize_location(row) for row in rows}


def serialize_location(row) -> dict:
	latitude = to_float(row.get("latitude"))
	longitude = to_float(row.get("longitude"))
	return {
		"name": row.name,
		"label": row.get("location") or row.name,
		"city": row.get("city"),
		"location_type": row.get("location_type"),
		"latitude": latitude,
		"longitude": longitude,
		"geolocated": bool(latitude and longitude),
	}


def build_route(loading, unloading) -> str:
	return " -> ".join(part for part in (loading, unloading) if part)
