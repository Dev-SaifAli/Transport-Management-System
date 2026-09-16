"""Explicit, repeatable setup for the basic TMS demo; never run on migration."""

import frappe

from transport_management.location_master import ensure_transport_location_fields
from transport_management.party_master import ensure_supplier_transport_fields
from transport_management.truck_master import ensure_owned_truck_fields

CUSTOMER = "ORYX CONCRETE PRODUCT LLC SAJJA"
NORMAL_SUPPLIER = "DEMO TMS GENERAL SUPPLIER"
TRANSPORTER_SUPPLIER = "DEMO TMS TRANSPORTER SUPPLIER"
HIRED_VEHICLE_PLATE = "HIRED-TRUCK-001"
DEMO_TRUCKS = ("29413-FUJ", "29414-FUJ", "29415-FUJ")
ORDER_MARKER = "DEMO TMS ORYX 80.8 | ATBT AL TAWEEN - SAJJA ORXY - 78"
TRIP_MARKER_PREFIX = "DEMO TMS ORYX TRANSPORT TRIP"
TRUCK_NOTE = (
	"DEMO ONLY: Make, model, manufacturing year, chassis and engine are unknown placeholders. "
	"Acquisition year 2000 and fuel type Diesel are DEMO placeholders, not verified technical facts. "
	"Replace before operational use. Driver phone DEMO-UMAIR is not a real phone number."
)


def _reuse_or_create(doctype, filters, values, or_filters=None):
	matches = frappe.get_all(doctype, filters=filters, or_filters=or_filters, pluck="name", limit=2)
	if len(matches) > 1:
		frappe.throw(f"Demo setup: multiple matching {doctype} records; resolve duplicates manually.")
	if matches:
		return frappe.get_doc(doctype, matches[0]), False
	doc = frappe.new_doc(doctype)
	doc.update(values)
	doc.insert()
	return doc, True


def _set_values_if_changed(doc, values):
	changed = False
	for fieldname, value in values.items():
		if doc.get(fieldname) != value:
			doc.set(fieldname, value)
			changed = True
	if changed:
		doc.save()


def _ensure_demo_truck(truck_number, driver, fuel_uom):
	truck, created = _reuse_or_create("Truck", {"truck_number": truck_number}, {
		"truck_number": truck_number,
		"license_plate": truck_number,
		"model": "DEMO - UNKNOWN",
		"make": "DEMO - UNKNOWN",
		"manufacturing_year": "DEMO - UNKNOWN",
		"acquisition_date": 2000,
		"fuel_type": "Diesel",
		"fuel_uom": fuel_uom,
		"chassis_number": f"DEMO-{truck_number}",
		"engine_number": "DEMO-UNKNOWN",
		"trans_ms_driver": driver,
		"status": "Idle",
		"disabled": 0,
		"ownership_type": "OWN",
	}, or_filters={"truck_number": truck_number, "license_plate": truck_number, "name": truck_number})
	if created:
		truck.add_comment("Comment", TRUCK_NOTE)
	if not truck.get("ownership_type"):
		truck.ownership_type = "OWN"
		truck.save()
	if truck.ownership_type != "OWN":
		frappe.throw(f"Existing demo Truck {truck.name} is not marked as owned; review it before demo setup.")
	if truck.disabled or truck.status != "Idle":
		frappe.throw(f"Existing demo Truck {truck.name} is not Idle/enabled; review it before demo setup.")
	return truck


def _ensure_demo_trip(job, demo, planned_quantity, sequence, vehicle):
	remarks = f"{TRIP_MARKER_PREFIX} {sequence}"
	trip_values = {
		"transport_job": job.name,
		"execution_source": "OWN",
		"trip_date": job.requested_date,
		"vehicle": vehicle,
		"driver": demo["driver"],
		"loading_site": job.loading_site,
		"unloading_site": job.unloading_site,
		"material": job.material,
		"planned_quantity": planned_quantity,
		"uom": job.uom,
		"remarks": remarks,
	}
	trip, created = _reuse_or_create("Transport Trip", {"transport_job": job.name, "remarks": remarks}, {
		**trip_values,
		"status": "PLANNED",
	})
	if created:
		return trip.name

	if trip.status in {"CLOSED", "CANCELLED"}:
		frappe.throw(f"Existing demo Transport Trip {trip.name} is {trip.status}; review it before demo setup.")
	_set_values_if_changed(trip, trip_values)
	return trip.name


def _normalize_existing_demo_trip_vehicles(job, vehicles):
	for sequence, vehicle in enumerate(vehicles, start=1):
		remarks = f"{TRIP_MARKER_PREFIX} {sequence}"
		trip = frappe.db.get_value(
			"Transport Trip",
			{"transport_job": job.name, "remarks": remarks},
			["name", "status"],
			as_dict=True,
		)
		if not trip:
			continue
		if trip.status in {"CLOSED", "CANCELLED"}:
			frappe.throw(f"Existing demo Transport Trip {trip.name} is {trip.status}; review it before demo setup.")
		frappe.db.set_value("Transport Trip", trip.name, "vehicle", vehicle, update_modified=False)


def setup_demo_data(country="United Arab Emirates"):
	"""Create/reuse requested masters and one standalone Transport Job.

	No commits: bench execute commits on success. On failure, undo this method's
	business records. Existing master records are reused without mutation. The
	marked demo Transport Job is updated in place so repeated runs stay idempotent.
	Run serially; this small demo helper is not a concurrent import service.
	"""
	ensure_transport_location_fields()
	ensure_supplier_transport_fields()
	ensure_owned_truck_fields()
	if not frappe.db.exists("Country", country):
		frappe.throw(f"Demo setup requires existing Country {country}.")

	frappe.db.savepoint("tms_demo_setup")
	try:
		customer, _ = _reuse_or_create("Customer", {"customer_name": CUSTOMER}, {
			"customer_name": CUSTOMER, "customer_type": "Company",
		})
		normal_supplier, normal_created = _reuse_or_create("Supplier", {"supplier_name": NORMAL_SUPPLIER}, {
			"supplier_name": NORMAL_SUPPLIER,
			"supplier_type": "Company",
			"is_transporter": 0,
		})
		if not normal_created and normal_supplier.is_transporter:
			frappe.throw("Existing demo normal Supplier is marked as a transporter; review it manually.")

		transporter_supplier, transporter_created = _reuse_or_create("Supplier", {"supplier_name": TRANSPORTER_SUPPLIER}, {
			"supplier_name": TRANSPORTER_SUPPLIER,
			"supplier_type": "Company",
			"is_transporter": 1,
			"transporter_status": "Active",
			"default_rate_type": "Per Trip",
		})
		if not transporter_created:
			if not transporter_supplier.is_transporter:
				frappe.throw("Existing demo Transporter Supplier is not marked as a transporter; review it manually.")
			if transporter_supplier.disabled:
				frappe.throw("Existing demo Transporter Supplier is disabled; review it manually.")
			if transporter_supplier.transporter_status != "Active":
				frappe.throw("Existing demo Transporter Supplier is not Active; review it manually.")
		hired_vehicle, _ = _reuse_or_create("Hired Vehicle", {
			"transporter": transporter_supplier.name,
			"plate_number": HIRED_VEHICLE_PLATE,
		}, {
			"transporter": transporter_supplier.name,
			"plate_number": HIRED_VEHICLE_PLATE,
			"active": 1,
		})
		if hired_vehicle.transporter != transporter_supplier.name:
			frappe.throw("Existing demo Hired Vehicle belongs to another Transporter; review it manually.")
		if hired_vehicle.plate_number != HIRED_VEHICLE_PLATE:
			frappe.throw("Existing demo Hired Vehicle has another plate number; review it manually.")
		if not hired_vehicle.active:
			hired_vehicle.active = 1
			hired_vehicle.save()
		locations = []
		location_values = (
			("ATBT AL TAWEEN", {"location_type": "Plant", "location_usage": "Loading", "active": 1}),
			("SAJJA ORYX", {
				"location_type": "Customer Site",
				"location_usage": "Unloading",
				"customer": customer.name,
				"active": 1,
			}),
		)
		for location, extra_values in location_values:
			doc, created = _reuse_or_create("Transport Location", {"location": location}, {
				"location": location,
				"country": country,
				**extra_values,
			})
			if doc.country != country:
				frappe.throw(f"Demo location {doc.name} belongs to another country; existing data left unchanged.")
			if not created:
				_set_values_if_changed(doc, extra_values)
			locations.append(doc.name)
		material, _ = _reuse_or_create("Cargo Types", {"cargo_name": "3/4 Aggregate"}, {
			"cargo_name": "3/4 Aggregate",
		})
		uom, _ = _reuse_or_create("UOM", {"uom_name": "TON"}, {"uom_name": "TON", "enabled": 1})
		if not uom.enabled:
			frappe.throw("Existing UOM TON is disabled; enable it explicitly before demo setup.")
		fuel_uom, _ = _reuse_or_create("UOM", {"uom_name": "Litre"}, {"uom_name": "Litre", "enabled": 1})
		if not fuel_uom.enabled:
			frappe.throw("Existing UOM Litre is disabled; enable it explicitly before demo setup.")
		driver, _ = _reuse_or_create("Truck Driver", {"full_name": "UMAIR"}, {
			"full_name": "UMAIR", "status": "Active", "cell_number": "DEMO-UMAIR",
			"address": "DEMO: contact/address details not supplied; phone is a placeholder.",
		})
		if driver.status != "Active":
			frappe.throw("Existing UMAIR driver is not Active; review it before demo setup.")
		trucks = [_ensure_demo_truck(truck_number, driver.name, fuel_uom.name) for truck_number in DEMO_TRUCKS]
		truck = trucks[0]

		job_values = {
			"customer": customer.name,
			"requested_date": "2026-09-09",
			"loading_site": locations[0],
			"unloading_site": locations[1],
			"material": material.name,
			"requested_quantity": 80.8,
			"uom": uom.name,
			"do_number": "1265986",
			"customer_do": "12-56362253",
			"sale_order_reference": "ATBT AL TAWEEN - SAJJA ORXY - 78",
			"fnrc": "620",
			"special_instructions": "DEMO: created from standalone TMS Transport Job setup.",
		}
		job_filters = {
			"customer": customer.name,
			"requested_date": "2026-09-09",
			"loading_site": locations[0],
			"unloading_site": locations[1],
			"material": material.name,
			"do_number": "1265986",
		}
		job, job_created = _reuse_or_create("Transport Job", job_filters, job_values)
		if job.customer != customer.name:
			frappe.throw("Existing marked demo Transport Job has another customer; review it manually.")
		if not job_created:
			_set_values_if_changed(job, job_values)
		demo = {
			"customer": customer.name, "normal_supplier": normal_supplier.name,
			"transporter_supplier": transporter_supplier.name, "hired_vehicle": hired_vehicle.name,
			"loading_site": locations[0], "offloading_site": locations[1],
			"material": material.name, "uom": uom.name, "fuel_uom": fuel_uom.name,
			"driver": driver.name, "vehicle": truck.name, "vehicles": [truck.name for truck in trucks],
			"transport_job": job.name,
			"note": "Demo uses the current Transport Job to Transport Trip flow. No rates, settlements, or invoices were automatically created.",
		}
		_normalize_existing_demo_trip_vehicles(job, demo["vehicles"])
		demo["transport_trips"] = [
			_ensure_demo_trip(job, demo, 30, 1, trucks[0].name),
			_ensure_demo_trip(job, demo, 30, 2, trucks[1].name),
			_ensure_demo_trip(job, demo, 20.8, 3, trucks[2].name),
		]
		return demo
	except Exception:
		frappe.db.rollback(save_point="tms_demo_setup")
		raise
