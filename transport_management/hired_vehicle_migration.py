"""Migration helpers for HIRED Transport Trip vehicle links."""

import frappe
from frappe import _


def migrate_hired_vehicle_text_to_links():
	"""Convert legacy Transport Trip.hired_vehicle text values into Hired Vehicle links."""
	if not frappe.db.table_exists("tabHired Vehicle"):
		return
	if not frappe.db.table_exists("tabTransport Trip"):
		return

	trips = frappe.get_all(
		"Transport Trip",
		filters={"execution_source": "HIRED", "hired_vehicle": ["is", "set"]},
		fields=["name", "transporter", "hired_vehicle"],
	)
	for trip in trips:
		if not trip.hired_vehicle:
			continue
		if frappe.db.exists("Hired Vehicle", trip.hired_vehicle):
			continue
		if not trip.transporter:
			frappe.throw(
				_("Cannot migrate Hired Vehicle value {0} on Transport Trip {1} without a Transporter.").format(
					frappe.bold(trip.hired_vehicle), frappe.bold(trip.name)
				)
			)

		hired_vehicle = get_or_create_hired_vehicle(trip.transporter, trip.hired_vehicle)
		frappe.db.set_value(
			"Transport Trip",
			trip.name,
			"hired_vehicle",
			hired_vehicle,
			update_modified=False,
		)

	validate_no_orphan_hired_vehicle_links()


def get_or_create_hired_vehicle(transporter, plate_number):
	existing = frappe.db.get_value(
		"Hired Vehicle",
		{"transporter": transporter, "plate_number": plate_number},
		"name",
	)
	if existing:
		return existing

	doc = frappe.new_doc("Hired Vehicle")
	doc.transporter = transporter
	doc.plate_number = plate_number
	doc.active = 1
	doc.insert(ignore_permissions=True)
	return doc.name


def validate_no_orphan_hired_vehicle_links():
	orphan_trips = []
	trips = frappe.get_all(
		"Transport Trip",
		filters={"execution_source": "HIRED", "hired_vehicle": ["is", "set"]},
		fields=["name", "hired_vehicle"],
	)
	for trip in trips:
		if trip.hired_vehicle and not frappe.db.exists("Hired Vehicle", trip.hired_vehicle):
			orphan_trips.append(f"{trip.name}: {trip.hired_vehicle}")

	if orphan_trips:
		frappe.throw(_("Unresolved Hired Vehicle links remain: {0}").format(", ".join(orphan_trips)))
