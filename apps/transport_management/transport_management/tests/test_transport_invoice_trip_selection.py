"""Focused tests for Transport Sales Invoice trip date selection."""

import unittest

import frappe

from transport_management.transport_management.doctype.transport_job.transport_job import (
	get_customer_transport_invoice_trips,
	get_transport_sales_invoice_payload,
	get_sales_order_billable_trips,
	validate_billing_date_range,
	validate_invoice_trips_not_already_billed,
)
from transport_management.tms_billing_setup import ensure_tms_billing_setup


class TestTransportInvoiceTripSelection(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		ensure_tms_billing_setup()

	def setUp(self):
		frappe.db.savepoint("transport_invoice_trip_selection")
		hash_id = frappe.generate_hash(length=8).upper()
		self.customer = f"TMS Test Customer {hash_id}"
		self.other_customer = f"Other TMS Test Customer {hash_id}"
		self.sales_order = f"TSO-RANGE-{hash_id}"
		self.job = self.insert_job(hash_id, self.customer)

	def tearDown(self):
		frappe.db.rollback(save_point="transport_invoice_trip_selection")

	def insert_job(self, hash_id, customer):
		name = f"TJOB-RANGE-{hash_id}"
		frappe.db.sql(
			"""
			insert into `tabTransport Job`
				(name, creation, modified, modified_by, owner, docstatus, idx,
				customer, requested_date, loading_site, unloading_site, material,
				requested_quantity, uom, status, sales_order, sales_order_item, agreed_rate)
			values
				(%(name)s, now(), now(), 'Administrator', 'Administrator', 0, 0,
				%(customer)s, '2026-09-01', 'MASAFI CRUSHER', 'AJMAN TECH REMIX', '3/4 Aggregate',
				500, 'TON', 'Pending', %(sales_order)s, %(sales_order_item)s, 25.5)
			""",
			{
				"name": name,
				"customer": customer,
				"sales_order": self.sales_order,
				"sales_order_item": f"TSO-ITEM-{hash_id}",
			},
		)
		return name

	def insert_trip(
		self,
		status,
		loading_datetime,
		delivery_datetime=None,
		loaded_quantity=10,
		delivered_quantity=10,
		transport_sales_invoice=None,
		transport_billing_status="Not Billed",
	):
		name = f"TTRIP-RANGE-{frappe.generate_hash(length=10).upper()}"
		frappe.db.sql(
			"""
			insert into `tabTransport Trip`
				(name, creation, modified, modified_by, owner, docstatus, idx,
				transport_job, trip_date, execution_source, hired_vehicle, hired_driver,
				material, loading_site, unloading_site, gdn, loading_no,
				loading_datetime, delivery_datetime, loaded_quantity, delivered_quantity,
				planned_quantity, uom, status, rak_toll, sharjah_toll, fnrc_extra_charge,
				transport_billing_status, transport_sales_invoice)
			values
				(%(name)s, now(), now(), 'Administrator', 'Administrator', 0, 0,
				%(transport_job)s, date(%(loading_datetime)s), 'HIRED', 'HV-RANGE-TEST', 'Driver Range Test',
				'3/4 Aggregate', 'MASAFI CRUSHER', 'AJMAN TECH REMIX', %(gdn)s, %(loading_no)s,
				%(loading_datetime)s, %(delivery_datetime)s, %(loaded_quantity)s, %(delivered_quantity)s,
				%(planned_quantity)s, 'TON', %(status)s, 0, 0, 0,
				%(transport_billing_status)s, %(transport_sales_invoice)s)
			""",
			{
				"name": name,
				"transport_job": self.job,
				"gdn": f"GDN-{name}",
				"loading_no": f"LOAD-{name}",
				"loading_datetime": loading_datetime,
				"delivery_datetime": delivery_datetime,
				"loaded_quantity": loaded_quantity,
				"delivered_quantity": delivered_quantity,
				"planned_quantity": loaded_quantity or delivered_quantity or 10,
				"status": status,
				"transport_billing_status": transport_billing_status,
				"transport_sales_invoice": transport_sales_invoice,
			},
		)
		return name

	def get_rows(self, from_date="2026-09-01", to_date="2026-09-15"):
		return get_sales_order_billable_trips(self.sales_order, from_date, to_date)

	def test_closed_trip_delivered_inside_range_is_included(self):
		trip = self.insert_trip("CLOSED", "2026-09-02 08:00:00", "2026-09-03 18:00:00")

		rows = self.get_rows()

		self.assertEqual([row.name for row in rows], [trip])

	def test_closed_trip_delivered_outside_range_is_excluded(self):
		self.insert_trip("CLOSED", "2026-09-16 08:00:00", "2026-09-17 18:00:00")

		self.assertEqual(self.get_rows(), [])

	def test_in_transit_trip_loaded_on_to_date_is_included(self):
		trip = self.insert_trip(
			"IN_TRANSIT",
			"2026-09-15 08:00:00",
			delivery_datetime=None,
			delivered_quantity=0,
		)

		rows = self.get_rows()

		self.assertEqual([row.name for row in rows], [trip])
		self.assertEqual(rows[0].status, "IN_TRANSIT")
		self.assertEqual(rows[0].loaded_quantity, 10)

	def test_closed_trip_loaded_on_to_date_delivered_after_range_is_included(self):
		trip = self.insert_trip("CLOSED", "2026-09-15 08:00:00", "2026-09-16 18:00:00")

		rows = self.get_rows()

		self.assertEqual([row.name for row in rows], [trip])

	def test_in_transit_trip_loaded_before_to_date_is_excluded(self):
		self.insert_trip("IN_TRANSIT", "2026-09-14 08:00:00", delivery_datetime=None)

		self.assertEqual(self.get_rows(), [])

	def test_trip_loaded_after_to_date_is_excluded(self):
		self.insert_trip("IN_TRANSIT", "2026-09-16 08:00:00", delivery_datetime=None)

		self.assertEqual(self.get_rows(), [])

	def test_cancelled_trip_loaded_on_to_date_is_excluded(self):
		self.insert_trip("CANCELLED", "2026-09-15 08:00:00", delivery_datetime=None)

		self.assertEqual(self.get_rows(), [])

	def test_already_invoiced_trip_is_excluded(self):
		self.insert_trip(
			"CLOSED",
			"2026-09-02 08:00:00",
			"2026-09-03 18:00:00",
			transport_sales_invoice="SINV-RANGE-OLD",
			transport_billing_status="Draft Invoice",
		)

		self.assertEqual(self.get_rows(), [])

	def test_wrong_customer_is_excluded(self):
		other_job = self.insert_job(f"OTHER-{frappe.generate_hash(length=5).upper()}", self.other_customer)
		current_job = self.job
		self.job = other_job
		self.insert_trip("CLOSED", "2026-09-02 08:00:00", "2026-09-03 18:00:00")
		self.job = current_job

		rows = get_customer_transport_invoice_trips(self.customer, "2026-09-01", "2026-09-15")

		self.assertEqual(rows["trips"], [])

	def test_last_day_trip_invoiced_in_previous_period_is_excluded_from_next_period(self):
		self.insert_trip(
			"CLOSED",
			"2026-09-15 08:00:00",
			"2026-09-16 18:00:00",
			transport_sales_invoice="SINV-PREVIOUS-PERIOD",
			transport_billing_status="Draft Invoice",
		)

		rows = self.get_rows("2026-09-16", "2026-09-30")

		self.assertEqual(rows, [])

	def test_duplicate_server_side_invoice_attempt_is_rejected(self):
		trip = self.insert_trip(
			"CLOSED",
			"2026-09-02 08:00:00",
			"2026-09-03 18:00:00",
			transport_sales_invoice="SINV-DUPLICATE",
			transport_billing_status="Draft Invoice",
		)

		with self.assertRaisesRegex(frappe.ValidationError, "already included in Sales Invoice SINV-DUPLICATE"):
			validate_invoice_trips_not_already_billed([trip])

	def test_loaded_quantity_fallback_is_used_for_last_day_in_transit_trip(self):
		trip = self.insert_trip(
			"IN_TRANSIT",
			"2026-09-15 08:00:00",
			delivery_datetime=None,
			loaded_quantity=12.5,
			delivered_quantity=0,
		)

		rows = get_customer_transport_invoice_trips(self.customer, "2026-09-01", "2026-09-15")

		self.assertEqual([row["trip"] for row in rows["trips"]], [trip])
		self.assertEqual(rows["trips"][0]["delivered_quantity"], 12.5)

	def test_sales_invoice_trip_selection_payload_populates_items(self):
		trip = self.insert_trip(
			"IN_TRANSIT",
			"2026-09-15 08:00:00",
			delivery_datetime=None,
			loaded_quantity=12.5,
			delivered_quantity=0,
		)

		payload = get_transport_sales_invoice_payload(
			self.customer,
			"2026-09-01",
			"2026-09-15",
			[trip],
		)

		self.assertEqual(payload["trip_names"], [trip])
		self.assertEqual(payload["header"]["customer"], self.customer)
		self.assertEqual(payload["header"]["tms_invoice_type"], "Transport")
		self.assertIn(trip, payload["header"]["tms_transport_trips"])
		self.assertEqual(len(payload["items"]), 1)
		self.assertEqual(payload["items"][0]["qty"], 12.5)
		self.assertEqual(payload["items"][0]["rate"], 25.5)
		self.assertEqual(payload["items"][0]["tms_transport_job"], self.job)

	def test_boundary_date_comparison_is_inclusive(self):
		first_day = self.insert_trip("CLOSED", "2026-09-01 08:00:00", "2026-09-01 18:00:00")
		last_day = self.insert_trip("CLOSED", "2026-09-15 08:00:00", "2026-09-15 18:00:00")

		rows = self.get_rows()

		self.assertEqual({row.name for row in rows}, {first_day, last_day})

	def test_from_date_after_to_date_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "From Date cannot be after To Date"):
			validate_billing_date_range("2026-09-16", "2026-09-15")
