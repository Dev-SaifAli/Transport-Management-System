"""Tests for BRD-aligned Transport Trip execution."""

import unittest

import frappe

from transport_management.cargo_type_master import (
	get_compatible_hired_vehicles,
	get_compatible_owned_trucks,
)
from transport_management.demo import setup_demo_data
from transport_management.party_master import ensure_supplier_transport_fields
from transport_management.transport_management.doctype.transport_trip.transport_trip import (
	get_defaults_from_transport_job,
)


class TestTransportTrip(unittest.TestCase):
	def setUp(self):
		frappe.db.savepoint("transport_trip_test")
		ensure_supplier_transport_fields()
		self.demo = setup_demo_data()
		self.job = frappe.get_doc("Transport Job", self.demo["transport_job"])
		self.set_compatible_demo_assignment()
		frappe.db.delete("Transport Trip", {"transport_job": self.job.name})

	def tearDown(self):
		frappe.db.rollback(save_point="transport_trip_test")

	def make_trip(self, **values):
		doc = frappe.new_doc("Transport Trip")
		doc.update({
			"transport_job": self.job.name,
			"execution_source": "OWN",
			"trip_date": self.job.requested_date,
			"vehicle": self.demo["vehicle"],
			"driver": self.demo["driver"],
			"loading_site": self.job.loading_site,
			"unloading_site": self.job.unloading_site,
			"material": self.job.material,
			"planned_quantity": 30,
			"uom": self.job.uom,
		})
		doc.update(values)
		return doc

	def set_compatible_demo_assignment(self, material="3/4 AGREEGAT(10MM-20MM)", truck_type="TIPPER"):
		frappe.db.set_value("Truck", self.demo["vehicle"], "vehicle_type", truck_type)
		frappe.db.set_value("Transport Job", self.job.name, "material", material)
		self.job.reload()

	def make_truck(self, vehicle_type=None, **values):
		doc = frappe.new_doc("Truck")
		hash_value = frappe.generate_hash(length=8)
		doc.update({
			"truck_number": "TMS-COMP-" + hash_value,
			"license_plate": "TMS-COMP-" + hash_value,
			"vehicle_type": vehicle_type,
			"ownership_type": "OWN",
			"status": "Idle",
			"disabled": 0,
		})
		doc.update(values)
		doc.insert()
		return doc

	def make_material(self, truck_types=(), active=1):
		doc = frappe.new_doc("Cargo Types")
		doc.cargo_name = "TMS COMP MATERIAL " + frappe.generate_hash(length=8)
		doc.active = active
		for truck_type in truck_types:
			doc.append("allowed_truck_types", {"truck_type": truck_type})
		doc.insert()
		return doc

	def make_job(self, material, **values):
		doc = frappe.new_doc("Transport Job")
		doc.update({
			"customer": self.demo["customer"],
			"requested_date": "2026-09-09",
			"loading_site": self.demo["loading_site"],
			"unloading_site": self.demo["offloading_site"],
			"material": material,
			"requested_quantity": 10,
			"uom": self.demo["uom"],
		})
		doc.update(values)
		doc.insert()
		return doc

	def make_supplier(self, **values):
		doc = frappe.new_doc("Supplier")
		doc.update({
			"supplier_name": "TMS Trip Supplier " + frappe.generate_hash(length=8),
			"supplier_type": "Company",
			"is_transporter": 1,
			"transporter_status": "Active",
		})
		doc.update(values)
		doc.insert()
		return doc

	def make_hired_vehicle(self, supplier=None, **values):
		if supplier is None:
			supplier = self.make_supplier()
		doc = frappe.new_doc("Hired Vehicle")
		doc.update({
			"transporter": supplier.name,
			"plate_number": "HV-" + frappe.generate_hash(length=8),
			"active": 1,
			"vehicle_type": "TIPPER",
		})
		doc.update(values)
		doc.insert()
		return doc

	def make_hired_trip(self, supplier=None, **values):
		hired_vehicle_provided = "hired_vehicle" in values
		if supplier is None and "transporter" not in values:
			supplier = self.make_supplier()
		transporter = values.pop("transporter", supplier.name if supplier else None)
		hired_vehicle = values.pop("hired_vehicle", None)
		if not hired_vehicle_provided and supplier:
			hired_vehicle = self.make_hired_vehicle(supplier=supplier).name
		trip_values = {
			"execution_source": "HIRED",
			"vehicle": None,
			"driver": None,
			"transporter": transporter,
			"hired_vehicle": hired_vehicle,
		}
		trip_values.update(values)
		return self.make_trip(**trip_values)

	def test_transport_trip_creation(self):
		doc = self.make_trip()
		doc.insert()
		self.assertRegex(doc.name, r"^TTRIP-\d{4}-\d{5}$")
		self.assertEqual(doc.status, "PLANNED")
		self.assertEqual(doc.execution_source, "OWN")
		self.assertEqual(doc.vehicle, self.demo["vehicle"])
		self.assertEqual(doc.driver, self.demo["driver"])

	def test_transport_job_required(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(transport_job=None).insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(transport_job="MISSING-JOB").insert()

	def test_positive_planned_quantity(self):
		for quantity in (0, -1):
			with self.subTest(quantity=quantity):
				with self.assertRaises(frappe.ValidationError):
					self.make_trip(planned_quantity=quantity).insert()

	def test_actual_quantity_cannot_be_negative(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(actual_quantity=-0.1).insert()
		self.make_trip(actual_quantity=0).insert()

	def test_loading_and_unloading_sites_must_differ(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(unloading_site=self.job.loading_site).insert()

	def test_one_transport_job_can_have_multiple_trips(self):
		trip_1 = self.make_trip(planned_quantity=30)
		trip_1.insert()
		trip_2 = self.make_trip(planned_quantity=50.8)
		trip_2.insert()
		self.assertEqual(frappe.db.count("Transport Trip", {"transport_job": self.job.name}), 2)

	def test_total_planned_quantity_cannot_exceed_requested_quantity(self):
		self.make_trip(planned_quantity=80).insert()
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_trip(planned_quantity=1).insert()
		message = str(raised.exception)
		self.assertIn("Requested Quantity", message)
		self.assertIn("Already Planned", message)
		self.assertIn("Remaining Quantity", message)
		self.assertIn("Attempted Quantity", message)

	def test_cancelled_trip_is_excluded_from_reservation(self):
		cancelled_trip = self.make_trip(planned_quantity=80)
		cancelled_trip.insert()
		cancelled_trip.status = "CANCELLED"
		cancelled_trip.save()
		self.make_trip(planned_quantity=80.8).insert()

	def test_over_allocation_rejected_on_update(self):
		trip_1 = self.make_trip(planned_quantity=40)
		trip_1.insert()
		trip_2 = self.make_trip(planned_quantity=40)
		trip_2.insert()
		trip_2.planned_quantity = 41
		with self.assertRaises(frappe.ValidationError):
			trip_2.save()

	def test_defaults_from_transport_job(self):
		defaults = get_defaults_from_transport_job(self.job.name)
		self.assertEqual(defaults["transport_job"], self.job.name)
		self.assertEqual(defaults["trip_date"], self.job.requested_date)
		self.assertEqual(defaults["loading_site"], self.job.loading_site)
		self.assertEqual(defaults["unloading_site"], self.job.unloading_site)
		self.assertEqual(defaults["material"], self.job.material)
		self.assertEqual(defaults["uom"], self.job.uom)
		self.assertNotIn("customer", defaults)
		self.assertNotIn("do_number", defaults)

	def test_tipper_material_returns_idle_enabled_tipper_trucks(self):
		tipper = self.make_truck("TIPPER")
		tanker = self.make_truck("TANKER")
		compatible = get_compatible_owned_trucks("3/4 AGREEGAT(10MM-20MM)")
		self.assertIn(tipper.name, compatible)
		self.assertNotIn(tanker.name, compatible)

	def test_tanker_material_returns_idle_enabled_tanker_trucks(self):
		tanker = self.make_truck("TANKER")
		tipper = self.make_truck("TIPPER")
		compatible = get_compatible_owned_trucks("CEMENT")
		self.assertIn(tanker.name, compatible)
		self.assertNotIn(tipper.name, compatible)

	def test_non_available_and_blank_type_trucks_are_excluded(self):
		disabled = self.make_truck("TIPPER", disabled=1)
		on_trip = self.make_truck("TIPPER", status="On Trip")
		maintenance = self.make_truck("TIPPER", status="Under Maintenance")
		blank_type = self.make_truck(None)
		compatible = get_compatible_owned_trucks("3/4 AGREEGAT(10MM-20MM)")
		self.assertNotIn(disabled.name, compatible)
		self.assertNotIn(on_trip.name, compatible)
		self.assertNotIn(maintenance.name, compatible)
		self.assertNotIn(blank_type.name, compatible)

	def test_tipper_material_returns_active_tipper_hired_vehicles(self):
		supplier = self.make_supplier()
		tipper = self.make_hired_vehicle(supplier=supplier, vehicle_type="TIPPER")
		tanker = self.make_hired_vehicle(supplier=supplier, vehicle_type="TANKER")
		compatible = get_compatible_hired_vehicles("3/4 AGREEGAT(10MM-20MM)", supplier.name)
		self.assertIn(tipper.name, compatible)
		self.assertNotIn(tanker.name, compatible)

	def test_tanker_material_returns_active_tanker_hired_vehicles(self):
		supplier = self.make_supplier()
		tanker = self.make_hired_vehicle(supplier=supplier, vehicle_type="TANKER")
		tipper = self.make_hired_vehicle(supplier=supplier, vehicle_type="TIPPER")
		compatible = get_compatible_hired_vehicles("CEMENT", supplier.name)
		self.assertIn(tanker.name, compatible)
		self.assertNotIn(tipper.name, compatible)

	def test_non_matching_hired_vehicles_are_excluded(self):
		supplier = self.make_supplier()
		other_supplier = self.make_supplier()
		wrong_transporter = self.make_hired_vehicle(supplier=other_supplier, vehicle_type="TIPPER")
		inactive = self.make_hired_vehicle(supplier=supplier, vehicle_type="TIPPER", active=0)
		blank_type = self.make_hired_vehicle(supplier=supplier, vehicle_type=None)
		compatible = get_compatible_hired_vehicles("3/4 AGREEGAT(10MM-20MM)", supplier.name)
		self.assertNotIn(wrong_transporter.name, compatible)
		self.assertNotIn(inactive.name, compatible)
		self.assertNotIn(blank_type.name, compatible)

	def test_incompatible_truck_rejected_server_side(self):
		self.set_compatible_demo_assignment(material="CEMENT", truck_type="TIPPER")
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_trip(material="CEMENT").insert()
		self.assertIn("not compatible with material", str(raised.exception))
		self.assertIn("TANKER", str(raised.exception))

	def test_compatible_truck_accepted_server_side(self):
		self.set_compatible_demo_assignment(material="CEMENT", truck_type="TANKER")
		trip = self.make_trip(material="CEMENT")
		trip.insert()
		self.assertEqual(trip.vehicle, self.demo["vehicle"])

	def test_material_without_allowed_truck_types_blocks_assignment(self):
		material = self.make_material()
		job = self.make_job(material.name)
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_trip(transport_job=job.name, material=material.name).insert()
		self.assertIn("No allowed truck types are configured", str(raised.exception))

	def test_compatible_hired_vehicle_accepted_server_side(self):
		self.set_compatible_demo_assignment(material="CEMENT")
		supplier = self.make_supplier()
		vehicle = self.make_hired_vehicle(supplier=supplier, vehicle_type="TANKER")
		trip = self.make_hired_trip(supplier=supplier, hired_vehicle=vehicle.name, material="CEMENT")
		trip.insert()
		self.assertEqual(trip.hired_vehicle, vehicle.name)

	def test_incompatible_hired_vehicle_rejected_server_side(self):
		self.set_compatible_demo_assignment(material="CEMENT")
		supplier = self.make_supplier()
		vehicle = self.make_hired_vehicle(supplier=supplier, vehicle_type="TIPPER")
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_hired_trip(supplier=supplier, hired_vehicle=vehicle.name, material="CEMENT").insert()
		self.assertIn("Hired Vehicle", str(raised.exception))
		self.assertIn("not compatible with material", str(raised.exception))
		self.assertIn("TANKER", str(raised.exception))

	def test_hired_vehicle_without_type_rejected_server_side(self):
		supplier = self.make_supplier()
		vehicle = self.make_hired_vehicle(supplier=supplier, vehicle_type=None)
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_hired_trip(supplier=supplier, hired_vehicle=vehicle.name).insert()
		self.assertIn("not compatible with material", str(raised.exception))

	def test_hired_material_without_allowed_truck_types_blocks_assignment(self):
		material = self.make_material()
		job = self.make_job(material.name)
		supplier = self.make_supplier()
		vehicle = self.make_hired_vehicle(supplier=supplier, vehicle_type="TIPPER")
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_hired_trip(
				supplier=supplier,
				hired_vehicle=vehicle.name,
				transport_job=job.name,
				material=material.name,
			).insert()
		self.assertIn("No allowed truck types are configured", str(raised.exception))

	def test_trip_material_must_match_transport_job_material(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(material="CEMENT").insert()

	def test_historical_legacy_material_trip_remains_readable_and_saveable(self):
		frappe.db.set_value("Truck", self.demo["vehicle"], "vehicle_type", None)
		frappe.db.set_value("Transport Job", self.job.name, "material", self.demo["material"])
		self.job.reload()
		trip = self.make_trip(material=self.demo["material"])
		trip.flags.ignore_validate = True
		trip.insert()
		trip.reload()
		trip.remarks = "Historical legacy material save"
		trip.save()
		self.assertEqual(trip.material, self.demo["material"])

	def test_vehicle_and_driver_remain_trip_owned(self):
		job_meta = frappe.get_meta("Transport Job")
		trip_meta = frappe.get_meta("Transport Trip")
		self.assertIsNone(job_meta.get_field("vehicle"))
		self.assertIsNone(job_meta.get_field("driver"))
		self.assertEqual(trip_meta.get_field("vehicle").options, "Truck")
		self.assertEqual(trip_meta.get_field("driver").options, "Truck Driver")
		self.assertEqual(trip_meta.get_field("vehicle").mandatory_depends_on, "eval:doc.execution_source == 'OWN'")
		self.assertEqual(trip_meta.get_field("driver").mandatory_depends_on, "eval:doc.execution_source == 'OWN'")
		self.assertEqual(trip_meta.get_field("hired_vehicle").fieldtype, "Link")
		self.assertEqual(trip_meta.get_field("hired_vehicle").options, "Hired Vehicle")

	def test_status_transition_validation(self):
		trip = self.make_trip()
		trip.insert()
		trip.status = "LOADED"
		with self.assertRaises(frappe.ValidationError):
			trip.save()

		trip.reload()
		for status in ("ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED"):
			trip.status = status
			trip.save()

		trip.status = "EXCEPTION"
		trip.save()
		self.assertEqual(trip.status, "EXCEPTION")

	def test_pod_required_for_pod_received(self):
		trip = self.make_trip()
		trip.insert()
		for status in ("ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED"):
			trip.status = status
			trip.save()
		trip.status = "POD_RECEIVED"
		with self.assertRaises(frappe.ValidationError):
			trip.save()

	def test_pod_received_at_is_set_once(self):
		trip = self.make_trip()
		trip.insert()
		for status in ("ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED"):
			trip.status = status
			trip.save()
		trip.status = "POD_RECEIVED"
		trip.pod_attachment = "/private/files/demo-pod.pdf"
		trip.save()
		self.assertTrue(trip.pod_received_at)
		original_timestamp = trip.pod_received_at
		trip.remarks = "Updated after POD"
		trip.save()
		self.assertEqual(trip.pod_received_at, original_timestamp)

	def test_closed_cannot_reopen(self):
		trip = self.make_trip()
		trip.insert()
		for status in ("ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED"):
			trip.status = status
			trip.save()
		trip.status = "POD_RECEIVED"
		trip.pod_attachment = "/private/files/demo-pod.pdf"
		trip.save()
		trip.status = "CLOSED"
		trip.save()
		trip.status = "DELIVERED"
		with self.assertRaises(frappe.ValidationError):
			trip.save()

	def test_own_trip_does_not_require_transporter(self):
		trip = self.make_trip(transporter=None)
		trip.insert()
		self.assertEqual(trip.execution_source, "OWN")
		self.assertFalse(trip.transporter)

	def test_own_trip_requires_vehicle_and_driver(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(vehicle=None).insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_trip(driver=None).insert()

	def test_hired_trip_accepts_active_transporter_supplier(self):
		trip = self.make_hired_trip()
		trip.insert()
		self.assertEqual(trip.execution_source, "HIRED")
		self.assertTrue(trip.transporter)
		hired_vehicle = frappe.get_doc("Hired Vehicle", trip.hired_vehicle)
		self.assertEqual(hired_vehicle.transporter, trip.transporter)
		self.assertTrue(hired_vehicle.active)
		self.assertFalse(trip.hired_driver)

	def test_hired_trip_requires_transporter_and_hired_vehicle(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_trip(transporter=None).insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_trip(hired_vehicle=None).insert()

	def test_hired_trip_rejects_non_transporter_supplier(self):
		supplier = self.make_supplier(is_transporter=0)
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_trip(supplier=supplier, hired_vehicle=self.demo["hired_vehicle"]).insert()

	def test_hired_trip_rejects_inactive_or_disabled_transporter(self):
		inactive = self.make_supplier(transporter_status="Inactive")
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_trip(supplier=inactive, hired_vehicle=self.demo["hired_vehicle"]).insert()

		disabled = self.make_supplier(disabled=1)
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_trip(supplier=disabled, hired_vehicle=self.demo["hired_vehicle"]).insert()

	def test_hired_trip_rejects_inactive_hired_vehicle(self):
		supplier = self.make_supplier()
		vehicle = self.make_hired_vehicle(supplier=supplier, active=0)
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_trip(supplier=supplier, hired_vehicle=vehicle.name).insert()

	def test_hired_trip_rejects_vehicle_from_another_transporter(self):
		supplier = self.make_supplier()
		other_supplier = self.make_supplier()
		vehicle = self.make_hired_vehicle(supplier=other_supplier)
		with self.assertRaises(frappe.ValidationError):
			self.make_hired_trip(supplier=supplier, hired_vehicle=vehicle.name).insert()
