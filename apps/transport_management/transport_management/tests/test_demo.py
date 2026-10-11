"""End-to-end demo verification with all business records rolled back."""

import unittest

import frappe

from transport_management.demo import setup_demo_data


class TestDemoSetup(unittest.TestCase):
	def test_repeatable_setup_creates_transport_job_and_trips_without_deleting_shipments(self):
		frappe.db.savepoint("tms_demo_test")
		try:
			shipment_count = frappe.db.count("Transport Shipment")
			first = setup_demo_data()
			self.assertEqual(first, setup_demo_data())
			self.assertEqual(frappe.db.count("Transport Shipment"), shipment_count)

			job = frappe.get_doc("Transport Job", first["transport_job"])
			self.assertEqual(job.customer, "ORYX CONCRETE PRODUCT LLC SAJJA")
			self.assertEqual(str(job.requested_date), "2026-09-09")
			self.assertEqual(job.loading_site, "ATBT AL TAWEEN")
			self.assertEqual(job.unloading_site, "SAJJA ORYX")
			loading_site = frappe.get_doc("Transport Location", job.loading_site)
			unloading_site = frappe.get_doc("Transport Location", job.unloading_site)
			self.assertEqual(loading_site.location_type, "Plant")
			self.assertTrue(loading_site.active)
			self.assertEqual(unloading_site.location_type, "Customer Site")
			self.assertEqual(unloading_site.customer, first["customer"])
			self.assertTrue(unloading_site.active)
			self.assertEqual(job.material, "3/4 Aggregate")
			self.assertEqual(job.requested_quantity, 80.8)
			self.assertEqual(job.do_number, "1265986")
			self.assertEqual(job.customer_do, "12-56362253")
			self.assertEqual(job.sale_order_reference, "ATBT AL TAWEEN - SAJJA ORXY - 78")
			self.assertEqual(job.fnrc, "620")

			normal_supplier = frappe.get_doc("Supplier", first["normal_supplier"])
			self.assertFalse(normal_supplier.is_transporter)
			transporter_supplier = frappe.get_doc("Supplier", first["transporter_supplier"])
			self.assertTrue(transporter_supplier.is_transporter)
			self.assertEqual(transporter_supplier.transporter_status, "Active")
			self.assertEqual(transporter_supplier.default_rate_type, "Per Trip")

			hired_vehicle = frappe.get_doc("Hired Vehicle", first["hired_vehicle"])
			self.assertEqual(hired_vehicle.transporter, first["transporter_supplier"])
			self.assertEqual(hired_vehicle.plate_number, "HIRED-TRUCK-001")
			self.assertTrue(hired_vehicle.active)

			truck = frappe.get_doc("Truck", first["vehicle"])
			self.assertEqual(truck.ownership_type, "OWN")
			self.assertEqual(truck.status, "Idle")
			self.assertFalse(truck.disabled)
			self.assertFalse(truck.capacity)
			self.assertFalse(truck.registration_expiry)
			self.assertFalse(truck.insurance_expiry)
			self.assertFalse(truck.erpnext_asset)

			self.assertEqual(len(first["transport_trips"]), 3)
			trips = frappe.get_all(
				"Transport Trip",
				filters={"transport_job": job.name},
				fields=["name", "planned_quantity", "status", "execution_source", "vehicle", "driver", "transporter"],
				order_by="planned_quantity desc, name asc",
			)
			self.assertEqual(sum(trip.planned_quantity for trip in trips), 80.8)
			self.assertEqual({trip.status for trip in trips}, {"PLANNED"})
			self.assertEqual({trip.execution_source for trip in trips}, {"OWN"})
			self.assertEqual({trip.vehicle for trip in trips}, set(first["vehicles"]))
			self.assertEqual({trip.driver for trip in trips}, {first["driver"]})
			self.assertEqual({trip.transporter for trip in trips}, {None})
		finally:
			frappe.db.rollback(save_point="tms_demo_test")
