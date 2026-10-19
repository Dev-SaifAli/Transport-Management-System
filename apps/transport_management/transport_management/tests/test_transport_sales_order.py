"""Tests for TMS Sales Order foundation and conversion to Transport Job."""

import unittest
from unittest.mock import patch

import frappe
from frappe.modules import reload_doc
from frappe.utils import getdate, now_datetime, today

from transport_management.demo import setup_demo_data
from transport_management.rbac import ensure_tms_rbac
from transport_management.tms_billing_setup import ensure_tms_billing_setup
from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
	create_quotation_transport_sales_order,
	create_transport_jobs,
	evaluate_sales_order_billing_status,
	ensure_ton_uom,
	get_quotation_sales_order_summary,
	get_transport_rate,
	resolve_quotation_sales_order_rate,
)
from transport_management.transport_management.doctype.transport_trip.transport_trip import (
	confirm_trip_loading,
	create_assigned_transport_trip,
	get_defaults_from_transport_job,
	get_trip_route_options,
	reject_trip_delivery_document,
	reject_trip_loading_document,
	verify_trip_delivery_document,
	verify_trip_loading_document,
)
from transport_management.transport_management.doctype.transport_job.transport_job import (
	evaluate_billing_readiness,
	get_billable_trips,
	get_customer_billable_trips,
	get_open_order_billable_trips,
	get_sales_order_billable_trips,
	group_sales_order_invoice_trips,
	sync_direct_transport_invoice_lifecycle,
	validate_invoice_trip_item_snapshot,
	validate_invoice_trips_not_already_billed,
)


class TestTransportSalesOrder(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_quotation_material", force=True)
		reload_doc("transport_management", "doctype", "transport_quotation_location", force=True)
		reload_doc("transport_management", "doctype", "transport_quotation_rate", force=True)
		reload_doc("transport_management", "doctype", "transport_quotation", force=True)
		reload_doc("transport_management", "doctype", "transport_job_permitted_loading_point", force=True)
		reload_doc("transport_management", "doctype", "transport_job_rate_snapshot", force=True)
		reload_doc("transport_management", "doctype", "transport_sales_order_rate_snapshot", force=True)
		reload_doc("transport_management", "doctype", "transport_sales_order", force=True)
		reload_doc("transport_management", "doctype", "transport_sales_order_loading_stop", force=True)
		reload_doc("transport_management", "doctype", "transport_sales_order_item", force=True)
		reload_doc("transport_management", "doctype", "transport_loading_stop", force=True)
		reload_doc("transport_management", "doctype", "transport_job", force=True)
		reload_doc("transport_management", "doctype", "transport_trip", force=True)
		reload_doc("transport_management", "doctype", "transport_trip_document", force=True)
		reload_doc("transport_management", "doctype", "transport_rate", force=True)
		ensure_ton_uom()
		ensure_tms_rbac()
		ensure_tms_billing_setup()

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("transport_sales_order_test")
		self.demo = setup_demo_data()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="transport_sales_order_test")

	def make_rate(self, **values):
		rate = frappe.new_doc("Transport Rate")
		rate.update({
			"customer": self.demo["customer"],
			"material": self.demo["material"],
			"loading_location": self.demo["loading_site"],
			"unloading_location": self.demo["offloading_site"],
			"rate": 20,
			"uom": "TON",
			"valid_from": "2026-01-01",
			"active": 1,
		})
		rate.update(values)
		rate.insert()
		return rate

	def make_sales_order(self, submit=False, ignore_permissions=False, **values):
		doc = frappe.new_doc("Transport Sales Order")
		doc.update({
			"posting_date": "2026-09-16",
			"customer": self.demo["customer"],
			"customer_lpo_number": "LPO-001",
			"remarks": "Test order",
			"items": [{
				"material": self.demo["material"],
				"quantity": 1000,
				"uom": "TON",
				"loading_location": self.demo["loading_site"],
				"unloading_location": self.demo["offloading_site"],
				"rate": 999,
				"amount": 999999,
			}],
		})
		for key, value in values.items():
			if key == "row":
				doc.items[0].update(value)
			else:
				doc.set(key, value)
		doc.insert(ignore_permissions=ignore_permissions)
		if submit:
			doc.submit()
		return doc

	def make_user(self, role_profile):
		email = f"{frappe.generate_hash(length=10).lower()}@tms-sales-order.test"
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"enabled": 1,
			"first_name": role_profile,
			"new_password": "TMSSales#2026",
			"role_profiles": [{"role_profile": role_profile}],
		})
		user.insert(ignore_permissions=True)
		frappe.clear_cache(user=email)
		return email

	def make_truck(self, vehicle_type="TIPPER"):
		doc = frappe.new_doc("Truck")
		hash_value = frappe.generate_hash(length=8)
		doc.update({
			"truck_number": "TMS-SO-" + hash_value,
			"license_plate": "TMS-SO-" + hash_value,
			"vehicle_type": vehicle_type,
			"ownership_type": "OWN",
			"status": "Idle",
			"disabled": 0,
		})
		doc.insert()
		return doc

	def make_loading_location(self, area_zone="North Zone"):
		location = frappe.new_doc("Transport Location")
		location.update({
			"location": "TMS SO Loading Stop " + frappe.generate_hash(length=8),
			"country": "United Arab Emirates",
			"location_usage": "Loading",
			"area_zone": area_zone,
			"active": 1,
		})
		location.insert()
		return location.name

	def make_destination(self, area_zone="Dubai Central"):
		location = frappe.new_doc("Transport Location")
		location.update({
			"location": "TMS SO Destination " + frappe.generate_hash(length=8),
			"country": "United Arab Emirates",
			"location_usage": "Unloading",
			"area_zone": area_zone,
			"active": 1,
		})
		location.insert()
		return location.name

	def make_loading_paper(self, trip, **values):
		document = frappe.new_doc("Transport Trip Document")
		document.update({
			"transport_trip": trip,
			"document_type": "LOADING_PAPER",
			"file": "/files/test-loading-paper.pdf",
			"uploaded_by_driver": self.demo["driver"],
		})
		document.update(values)
		document.insert(ignore_permissions=True)
		return document

	def make_approved_quotation(self, multiple_routes=False, multi_area=False, approved=True, **values):
		materials = [self.demo["material"]]
		loadings = [self.demo["loading_site"]]
		destinations = [self.demo["offloading_site"]]
		if multiple_routes:
			second_material = frappe.get_doc({
				"doctype": "Cargo Types",
				"cargo_name": "TMS SO Quotation Material " + frappe.generate_hash(length=8),
				"active": 1,
			}).insert().name
			materials.append(second_material)
			loadings.append(self.make_loading_location(area_zone="North Zone"))
			destinations.append(self.make_destination())

		if multi_area:
			south_loading = self.make_loading_location(area_zone="South Zone")
			loadings.append(south_loading)
			destinations.append(self.make_destination(area_zone="Abu Dhabi Industrial"))

		quotation = frappe.new_doc("Transport Quotation")
		quotation.update({
			"quotation_date": today(),
			"valid_until": today(),
			"service_period_from": "2026-01-01",
			"service_period_to": "2027-12-31",
			"customer": self.demo["customer"],
			"currency": "AED",
			"customer_approval_date": today(),
		})
		quotation.update(values)
		for material in materials:
			quotation.append("materials", {"material": material})
			for loading in loadings:
				quotation.append("locations", {
					"material": material,
					"location_role": "Loading",
					"location": loading,
				})
			for destination in destinations:
				quotation.append("locations", {
					"material": material,
					"location_role": "Destination",
					"location": destination,
				})

		rate = 25
		for material in materials:
			for loading in loadings:
				for destination in destinations:
					quotation.append("rates", {
						"material": material,
						"loading_location": loading,
						"unloading_location": destination,
						"rate": rate,
						"effective_from": "2026-01-01",
						"effective_to": "2027-12-31",
					})
					rate += 5
		quotation.insert()
		if approved:
			quotation.submit()
		return quotation

	def test_naming_series_and_customer_link_use_erpnext_customer(self):
		self.make_rate()
		doc = self.make_sales_order()
		self.assertRegex(doc.name, r"^TSO-\d{4}-\d{5}$")
		self.assertEqual(doc.order_mode, "Fixed Quantity")
		field = frappe.get_meta("Transport Sales Order").get_field("customer")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Customer")
		self.assertFalse(frappe.db.exists("DocType", "TMS Customer"))

	def test_row_uom_is_fixed_to_ton(self):
		self.make_rate()
		doc = self.make_sales_order(row={"uom": ""})
		self.assertEqual(doc.items[0].uom, "TON")
		with self.assertRaises(frappe.ValidationError):
			self.make_sales_order(row={"uom": "Tonne"})

	def test_quantity_must_be_positive(self):
		self.make_rate()
		for quantity in (0, -1):
			with self.subTest(quantity=quantity):
				with self.assertRaises(frappe.ValidationError):
					self.make_sales_order(row={"quantity": quantity})

	def test_amount_and_net_amount_are_recalculated_server_side(self):
		self.make_rate(rate=20)
		doc = self.make_sales_order()
		self.assertEqual(doc.items[0].rate, 20)
		self.assertEqual(doc.items[0].rate_source, "Transport Rate")
		self.assertEqual(doc.items[0].amount, 20000)
		self.assertEqual(doc.net_amount, 20000)

	def test_multiple_rows_sum_net_amount(self):
		self.make_rate(rate=20)
		doc = frappe.new_doc("Transport Sales Order")
		doc.update({
			"posting_date": "2026-09-16",
			"customer": self.demo["customer"],
			"items": [
				{
					"material": self.demo["material"],
					"quantity": 1000,
					"uom": "TON",
					"loading_location": self.demo["loading_site"],
					"unloading_location": self.demo["offloading_site"],
				},
				{
					"material": self.demo["material"],
					"quantity": 500,
					"uom": "TON",
					"loading_location": self.demo["loading_site"],
					"unloading_location": self.demo["offloading_site"],
				},
			],
		})
		doc.insert()
		self.assertEqual(doc.net_amount, 30000)

	def test_location_usage_is_enforced_server_side(self):
		self.make_rate()
		with self.assertRaises(frappe.ValidationError):
			self.make_sales_order(row={"loading_location": self.demo["offloading_site"]})
		with self.assertRaises(frappe.ValidationError):
			self.make_sales_order(row={"unloading_location": self.demo["loading_site"]})

	def test_location_query_fields_exist_for_client_filters(self):
		self.assertEqual(frappe.db.get_value("Transport Location", self.demo["loading_site"], "location_usage"), "Loading")
		self.assertEqual(frappe.db.get_value("Transport Location", self.demo["offloading_site"], "location_usage"), "Unloading")

	def test_rate_lookup_filters_date_customer_material_and_route(self):
		self.make_rate(rate=20)
		other_customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "TMS Rate Other Customer " + frappe.generate_hash(length=8),
			"customer_type": "Company",
		}).insert()
		self.make_rate(rate=99, customer=other_customer.name)
		self.assertEqual(
			get_transport_rate(
				self.demo["customer"],
				self.demo["material"],
				self.demo["loading_site"],
				self.demo["offloading_site"],
				"2026-09-16",
			),
			20,
		)

	def test_expired_and_future_rates_are_excluded(self):
		self.make_rate(valid_from="2026-01-01", valid_to="2026-02-01")
		self.make_rate(valid_from="2026-12-01")
		with self.assertRaises(frappe.ValidationError):
			get_transport_rate(
				self.demo["customer"],
				self.demo["material"],
				self.demo["loading_site"],
				self.demo["offloading_site"],
				"2026-09-16",
			)

	def test_no_rate_blocks_submit_but_not_draft(self):
		doc = self.make_sales_order()
		self.assertFalse(doc.items[0].rate)
		with self.assertRaises(frappe.ValidationError):
			doc.submit()

	def test_overlapping_matching_rates_raise_error(self):
		self.make_rate(rate=20)
		self.make_rate(rate=25)
		with self.assertRaises(frappe.ValidationError):
			self.make_sales_order()

	def test_rate_cannot_be_spoofed_via_api(self):
		self.make_rate(rate=20)
		doc = self.make_sales_order(row={"rate": 1, "amount": 1})
		self.assertEqual(doc.items[0].rate, 20)
		self.assertEqual(doc.items[0].amount, 20000)

	def test_manager_can_enable_manual_rate_override(self):
		manager_user = self.make_user("Transport Manager")
		frappe.set_user(manager_user)
		doc = self.make_sales_order(row={"manual_rate_override": 1, "rate": 33})
		self.assertEqual(doc.items[0].manual_rate_override, 1)
		self.assertEqual(doc.items[0].rate, 33)
		self.assertEqual(doc.items[0].rate_source, "Manual Override")

	def test_admin_can_enable_manual_rate_override(self):
		admin_user = self.make_user("Transport Admin")
		frappe.set_user(admin_user)
		doc = self.make_sales_order(row={"manual_rate_override": 1, "rate": 34})
		self.assertEqual(doc.items[0].manual_rate_override, 1)
		self.assertEqual(doc.items[0].rate, 34)
		self.assertEqual(doc.items[0].rate_source, "Manual Override")

	def test_trip_entry_user_cannot_override_rate(self):
		trip_user = self.make_user("TMS Trip Data Entry")
		frappe.set_user(trip_user)
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"You are not permitted to override Transport Rates manually.",
		):
			self.make_sales_order(
				ignore_permissions=True,
				row={"manual_rate_override": 1, "rate": 35},
			)

	def test_manual_override_works_without_transport_rate_record(self):
		doc = self.make_sales_order(submit=True, row={"manual_rate_override": 1, "rate": 42})
		self.assertEqual(doc.items[0].rate, 42)
		self.assertEqual(doc.items[0].amount, 42000)
		self.assertEqual(doc.net_amount, 42000)

	def test_manual_rate_must_be_positive(self):
		for rate in (0, -1):
			with self.subTest(rate=rate):
				with self.assertRaises(frappe.ValidationError):
					self.make_sales_order(row={"manual_rate_override": 1, "rate": rate})

	def test_backend_does_not_overwrite_manual_rate(self):
		self.make_rate(rate=20)
		doc = self.make_sales_order(row={"manual_rate_override": 1, "rate": 55})
		self.assertEqual(doc.items[0].rate, 55)
		self.assertEqual(doc.items[0].amount, 55000)
		self.assertEqual(doc.net_amount, 55000)
		self.assertEqual(doc.items[0].rate_source, "Manual Override")

	def test_switching_manual_override_off_returns_to_backend_rate_lookup(self):
		doc = self.make_sales_order(row={"manual_rate_override": 1, "rate": 55})
		self.make_rate(rate=20)
		doc.items[0].manual_rate_override = 0
		doc.save()
		self.assertEqual(doc.items[0].rate, 20)
		self.assertEqual(doc.items[0].amount, 20000)
		self.assertEqual(doc.net_amount, 20000)
		self.assertEqual(doc.items[0].rate_source, "Transport Rate")

	def test_submitted_sales_order_creates_one_transport_job_per_row(self):
		self.make_rate(rate=20)
		doc = self.make_sales_order(submit=True)
		jobs = create_transport_jobs(doc.name)
		self.assertEqual(len(jobs), 1)
		job = frappe.get_doc("Transport Job", jobs[0])
		row = frappe.get_doc("Transport Sales Order", doc.name).items[0]
		self.assertEqual(job.sales_order, doc.name)
		self.assertEqual(job.sales_order_item, row.name)
		self.assertEqual(job.customer, doc.customer)
		self.assertEqual(job.customer_lpo_number, doc.customer_lpo_number)
		self.assertEqual(job.quantity_mode, "Fixed Quantity")
		self.assertEqual(job.material, row.material)
		self.assertEqual(job.requested_quantity, row.quantity)
		self.assertEqual(job.uom, "TON")
		self.assertEqual(job.loading_site, row.loading_location)
		self.assertEqual(job.unloading_site, row.unloading_location)
		self.assertEqual(job.agreed_rate, row.rate)
		self.assertEqual(job.ordered_amount, row.amount)
		self.assertFalse(job.get("vehicle"))
		self.assertFalse(job.get("driver"))
		self.assertEqual(row.transport_job, job.name)
		self.assertEqual(row.converted, 1)

	def test_quotation_conversion_snapshots_all_material_routes_and_estimates(self):
		quotation = self.make_approved_quotation(
			multiple_routes=True,
			estimated_quantity=1250,
			estimated_trips=45,
		)
		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)

		self.assertEqual(order.docstatus, 0)
		self.assertEqual(order.order_mode, "Quotation-backed Open")
		self.assertEqual(order.transport_quotation, quotation.name)
		self.assertEqual(order.customer, quotation.customer)
		self.assertEqual(order.currency, "AED")
		self.assertEqual(order.estimated_quantity, 1250)
		self.assertEqual(order.estimated_trips, 45)
		self.assertEqual(order.items, [])
		self.assertEqual(order.ordered_quantity, 0)
		self.assertEqual(order.net_amount, 0)
		self.assertEqual(len(order.rate_snapshots), len(quotation.rates))
		self.assertEqual({row.material for row in order.rate_snapshots}, {row.material for row in quotation.materials})
		self.assertEqual(len({row.loading_location for row in order.rate_snapshots}), 2)
		self.assertEqual(len({row.unloading_location for row in order.rate_snapshots}), 2)
		for snapshot, source in zip(order.rate_snapshots, quotation.rates):
			self.assertEqual(snapshot.source_quotation_rate, source.name)
			self.assertEqual(snapshot.material, source.material)
			self.assertEqual(snapshot.loading_location, source.loading_location)
			self.assertEqual(snapshot.unloading_location, source.unloading_location)
			self.assertEqual(getdate(snapshot.effective_from), getdate(source.effective_from))
			self.assertEqual(getdate(snapshot.effective_to), getdate(source.effective_to))
			self.assertEqual(snapshot.currency, "AED")
			self.assertEqual(snapshot.rate, source.rate)

	def test_quotation_conversion_rejects_unsubmitted_quotation(self):
		quotation = self.make_approved_quotation(approved=False)
		with self.assertRaises(frappe.ValidationError):
			create_quotation_transport_sales_order(quotation.name)

	def test_quotation_order_rejects_customer_mismatch(self):
		quotation = self.make_approved_quotation()
		other_customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "TMS SO Other Customer " + frappe.generate_hash(length=8),
			"customer_type": "Company",
		}).insert(ignore_permissions=True)
		order = frappe.new_doc("Transport Sales Order")
		order.update({
			"order_mode": "Quotation-backed Open",
			"transport_quotation": quotation.name,
			"customer": other_customer.name,
			"currency": "AED",
		})
		source = quotation.rates[0]
		order.append("rate_snapshots", {
			"source_quotation_rate": source.name,
			"material": source.material,
			"loading_location": source.loading_location,
			"unloading_location": source.unloading_location,
			"effective_from": source.effective_from,
			"effective_to": source.effective_to,
			"currency": "AED",
			"rate": source.rate,
		})
		with self.assertRaises(frappe.ValidationError):
			order.insert()

	def test_quotation_rate_selection_must_belong_to_source(self):
		quotation = self.make_approved_quotation()
		with self.assertRaises(frappe.ValidationError):
			create_quotation_transport_sales_order(quotation.name, ["not-a-rate-row"])

	def test_quotation_order_rate_resolution_uses_loading_date_and_rejects_gaps(self):
		quotation = self.make_approved_quotation(multiple_routes=True)
		selected_rate = quotation.rates[0]
		order_name = create_quotation_transport_sales_order(quotation.name, [selected_rate.name])
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()

		resolved = resolve_quotation_sales_order_rate(
			order.name,
			selected_rate.material,
			selected_rate.loading_location,
			selected_rate.unloading_location,
			"2026-06-15",
		)
		self.assertEqual(resolved["source_quotation_rate"], selected_rate.name)
		self.assertEqual(resolved["rate"], selected_rate.rate)
		with self.assertRaises(frappe.ValidationError):
			resolve_quotation_sales_order_rate(
				order.name,
				selected_rate.material,
				selected_rate.loading_location,
				selected_rate.unloading_location,
				"2028-01-01",
			)
		with self.assertRaises(frappe.ValidationError):
			resolve_quotation_sales_order_rate(
				order.name,
				quotation.rates[-1].material,
				quotation.rates[-1].loading_location,
				quotation.rates[-1].unloading_location,
				"2026-06-15",
			)

	def test_submitted_quotation_order_rate_snapshots_are_immutable(self):
		quotation = self.make_approved_quotation()
		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()
		order.rate_snapshots[0].rate += 1

		with self.assertRaises(frappe.ValidationError):
			order.save()

	def test_quotation_estimates_are_optional_and_do_not_create_quantity_limits(self):
		quotation = self.make_approved_quotation()
		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)

		self.assertFalse(order.estimated_quantity)
		self.assertFalse(order.estimated_trips)
		self.assertEqual(order.items, [])
		self.assertEqual(order.ordered_quantity, 0)

	def test_open_order_creates_jobs_per_material_and_destination_with_traceability(self):
		quotation = self.make_approved_quotation(
			multiple_routes=True,
			estimated_quantity=100,
			estimated_trips=2,
		)
		order = frappe.get_doc(
			"Transport Sales Order",
			create_quotation_transport_sales_order(quotation.name),
		)
		order.submit()

		job_names = create_transport_jobs(order.name)
		jobs = [frappe.get_doc("Transport Job", name) for name in job_names]
		# 2 distinct materials in quotation -> exactly 2 Jobs
		self.assertEqual(len(jobs), 2)
		self.assertEqual(
			{job.material for job in jobs},
			{row.material for row in order.rate_snapshots},
		)
		for job in jobs:
			snapshots = [
				row
				for row in order.rate_snapshots
				if row.material == job.material
			]
			self.assertEqual(job.quantity_mode, "Open")
			self.assertEqual(job.requested_quantity, 0)
			self.assertFalse(job.estimated_quantity)
			self.assertEqual(job.sales_order, order.name)
			self.assertEqual(job.transport_quotation, quotation.name)
			self.assertEqual(job.customer, order.customer)
			self.assertFalse(job.sales_order_item)
			self.assertFalse(job.agreed_rate)
			self.assertEqual(
				{row.sales_order_rate_snapshot for row in job.sales_order_rate_snapshots},
				{row.name for row in snapshots},
			)
			self.assertEqual(
				{row.loading_location for row in job.permitted_loading_points},
				{row.loading_location for row in snapshots},
			)
			self.assertEqual(
				set(job.get_permitted_destinations()),
				{row.unloading_location for row in snapshots},
			)
			self.assertFalse(job.loading_stops)
			job.permitted_loading_points.pop()
			with self.assertRaises(frappe.ValidationError):
				job.save()
		self.assertEqual(frappe.db.get_value("Transport Sales Order", order.name, "status"), "Converted")

	def test_one_material_with_multiple_destinations_creates_one_job(self):
		dest1 = self.make_destination(area_zone="Dubai Central")
		dest2 = self.make_destination(area_zone="Sharjah Industrial")
		quotation = frappe.new_doc("Transport Quotation")
		quotation.update({
			"quotation_date": today(),
			"valid_until": today(),
			"customer": self.demo["customer"],
			"currency": "AED",
			"customer_approval_date": today(),
		})
		quotation.append("materials", {"material": self.demo["material"]})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Loading", "location": self.demo["loading_site"]})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Destination", "location": dest1})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Destination", "location": dest2})
		quotation.append("rates", {"material": self.demo["material"], "loading_location": self.demo["loading_site"], "unloading_location": dest1, "rate": 25, "effective_from": "2026-01-01", "effective_to": "2027-12-31"})
		quotation.append("rates", {"material": self.demo["material"], "loading_location": self.demo["loading_site"], "unloading_location": dest2, "rate": 30, "effective_from": "2026-01-01", "effective_to": "2027-12-31"})
		quotation.insert()
		quotation.submit()

		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()

		# Conversion must create exactly 1 Job for this material despite 2 destinations
		job_names = create_transport_jobs(order.name)
		self.assertEqual(len(job_names), 1)

		job = frappe.get_doc("Transport Job", job_names[0])
		self.assertEqual(job.material, self.demo["material"])
		self.assertEqual(len(job.sales_order_rate_snapshots), 2)
		self.assertEqual(set(job.get_permitted_destinations()), {dest1, dest2})
		self.assertEqual(frappe.db.get_value("Transport Sales Order", order.name, "status"), "Converted")

	def test_two_materials_create_two_jobs(self):
		second_material = frappe.get_doc({
			"doctype": "Cargo Types",
			"cargo_name": "TMS SO Phase 2 Mat " + frappe.generate_hash(length=8),
			"active": 1,
		}).insert().name

		dest1 = self.make_destination()
		quotation = frappe.new_doc("Transport Quotation")
		quotation.update({
			"quotation_date": today(),
			"valid_until": today(),
			"customer": self.demo["customer"],
			"currency": "AED",
			"customer_approval_date": today(),
		})
		quotation.append("materials", {"material": self.demo["material"]})
		quotation.append("materials", {"material": second_material})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Loading", "location": self.demo["loading_site"]})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Destination", "location": dest1})
		quotation.append("locations", {"material": second_material, "location_role": "Loading", "location": self.demo["loading_site"]})
		quotation.append("locations", {"material": second_material, "location_role": "Destination", "location": dest1})
		quotation.append("rates", {"material": self.demo["material"], "loading_location": self.demo["loading_site"], "unloading_location": dest1, "rate": 25, "effective_from": "2026-01-01", "effective_to": "2027-12-31"})
		quotation.append("rates", {"material": second_material, "loading_location": self.demo["loading_site"], "unloading_location": dest1, "rate": 35, "effective_from": "2026-01-01", "effective_to": "2027-12-31"})
		quotation.insert()
		quotation.submit()

		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()

		job_names = create_transport_jobs(order.name)
		self.assertEqual(len(job_names), 2)
		jobs = [frappe.get_doc("Transport Job", n) for n in job_names]
		self.assertEqual({j.material for j in jobs}, {self.demo["material"], second_material})
		self.assertEqual(frappe.db.get_value("Transport Sales Order", order.name, "status"), "Converted")

	def test_multiple_loading_points_and_routes_preserved_on_job(self):
		second_loading = self.make_loading_location(area_zone="North Zone")
		dest1 = self.make_destination()
		dest2 = self.make_destination()

		quotation = frappe.new_doc("Transport Quotation")
		quotation.update({
			"quotation_date": today(),
			"valid_until": today(),
			"customer": self.demo["customer"],
			"currency": "AED",
			"customer_approval_date": today(),
		})
		quotation.append("materials", {"material": self.demo["material"]})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Loading", "location": self.demo["loading_site"]})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Loading", "location": second_loading})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Destination", "location": dest1})
		quotation.append("locations", {"material": self.demo["material"], "location_role": "Destination", "location": dest2})
		# 2 loadings x 2 destinations = 4 rates
		for l in (self.demo["loading_site"], second_loading):
			for d in (dest1, dest2):
				quotation.append("rates", {"material": self.demo["material"], "loading_location": l, "unloading_location": d, "rate": 28, "effective_from": "2026-01-01", "effective_to": "2027-12-31"})
		quotation.insert()
		quotation.submit()

		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()

		job_names = create_transport_jobs(order.name)
		self.assertEqual(len(job_names), 1)

		job = frappe.get_doc("Transport Job", job_names[0])
		self.assertEqual(len(job.sales_order_rate_snapshots), 4)
		self.assertEqual({p.loading_location for p in job.permitted_loading_points}, {self.demo["loading_site"], second_loading})
		self.assertEqual(set(job.get_permitted_destinations()), {dest1, dest2})
		routes = job.get_permitted_routes()
		self.assertEqual(len(routes), 4)
		self.assertEqual({(r["loading_location"], r["unloading_location"]) for r in routes}, {
			(self.demo["loading_site"], dest1),
			(self.demo["loading_site"], dest2),
			(second_loading, dest1),
			(second_loading, dest2),
		})

	def test_duplicate_job_creation_rejected(self):
		quotation = self.make_approved_quotation()
		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()

		jobs = create_transport_jobs(order.name)
		self.assertEqual(len(jobs), 1)

		with self.assertRaisesRegex(frappe.ValidationError, "already been converted"):
			create_transport_jobs(order.name)

	def test_partial_conversion_by_material(self):
		second_material = frappe.get_doc({
			"doctype": "Cargo Types",
			"cargo_name": "TMS SO Partial Mat " + frappe.generate_hash(length=8),
			"active": 1,
		}).insert().name

		dest = self.make_destination()
		quotation = frappe.new_doc("Transport Quotation")
		quotation.update({
			"quotation_date": today(),
			"valid_until": today(),
			"customer": self.demo["customer"],
			"currency": "AED",
			"customer_approval_date": today(),
		})
		for mat in (self.demo["material"], second_material):
			quotation.append("materials", {"material": mat})
			quotation.append("locations", {"material": mat, "location_role": "Loading", "location": self.demo["loading_site"]})
			quotation.append("locations", {"material": mat, "location_role": "Destination", "location": dest})
			quotation.append("rates", {"material": mat, "loading_location": self.demo["loading_site"], "unloading_location": dest, "rate": 30, "effective_from": "2026-01-01", "effective_to": "2027-12-31"})
		quotation.insert()
		quotation.submit()

		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()

		# Convert only first material
		mat1_snapshots = [r.name for r in order.rate_snapshots if r.material == self.demo["material"]]
		jobs1 = create_transport_jobs(order.name, mat1_snapshots)
		self.assertEqual(len(jobs1), 1)
		self.assertEqual(frappe.db.get_value("Transport Sales Order", order.name, "status"), "Partially Converted")

		# Converting first material again raises duplicate error
		with self.assertRaisesRegex(frappe.ValidationError, "already exists for Material"):
			create_transport_jobs(order.name, mat1_snapshots)

		# Convert second material
		mat2_snapshots = [r.name for r in order.rate_snapshots if r.material == second_material]
		jobs2 = create_transport_jobs(order.name, mat2_snapshots)
		self.assertEqual(len(jobs2), 1)
		self.assertEqual(frappe.db.get_value("Transport Sales Order", order.name, "status"), "Converted")

	def test_cross_material_rate_snapshot_rejected(self):
		second_material = frappe.get_doc({
			"doctype": "Cargo Types",
			"cargo_name": "TMS SO Cross Mat " + frappe.generate_hash(length=8),
			"active": 1,
		}).insert().name

		dest = self.make_destination()
		quotation = frappe.new_doc("Transport Quotation")
		quotation.update({
			"quotation_date": today(),
			"valid_until": today(),
			"customer": self.demo["customer"],
			"currency": "AED",
			"customer_approval_date": today(),
		})
		for mat in (self.demo["material"], second_material):
			quotation.append("materials", {"material": mat})
			quotation.append("locations", {"material": mat, "location_role": "Loading", "location": self.demo["loading_site"]})
			quotation.append("locations", {"material": mat, "location_role": "Destination", "location": dest})
			quotation.append("rates", {"material": mat, "loading_location": self.demo["loading_site"], "unloading_location": dest, "rate": 30, "effective_from": "2026-01-01", "effective_to": "2027-12-31"})
		quotation.insert()
		quotation.submit()

		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()

		# Build a job for Material 1 but with Material 2's snapshot
		mat2_snapshot = [r for r in order.rate_snapshots if r.material == second_material][0]
		job = frappe.new_doc("Transport Job")
		job.update({
			"customer": order.customer,
			"requested_date": order.posting_date,
			"quantity_mode": "Open",
			"requested_quantity": 0,
			"uom": "TON",
			"material": self.demo["material"],
			"unloading_site": dest,
			"loading_site": self.demo["loading_site"],
			"sales_order": order.name,
			"transport_quotation": quotation.name,
		})
		job.append("sales_order_rate_snapshots", {"sales_order_rate_snapshot": mat2_snapshot.name})
		job.append("permitted_loading_points", {"loading_location": self.demo["loading_site"]})
		with self.assertRaisesRegex(frappe.ValidationError, "must match its rate snapshot material"):
			job.insert()

	def test_unauthorized_rate_snapshot_rejected(self):
		quotation1 = self.make_approved_quotation()
		order1 = frappe.get_doc("Transport Sales Order", create_quotation_transport_sales_order(quotation1.name))
		order1.submit()

		quotation2 = self.make_approved_quotation()
		order2 = frappe.get_doc("Transport Sales Order", create_quotation_transport_sales_order(quotation2.name))
		order2.submit()

		foreign_snapshot = order2.rate_snapshots[0]
		job = frappe.new_doc("Transport Job")
		job.update({
			"customer": order1.customer,
			"requested_date": order1.posting_date,
			"quantity_mode": "Open",
			"requested_quantity": 0,
			"uom": "TON",
			"material": self.demo["material"],
			"unloading_site": self.demo["offloading_site"],
			"loading_site": self.demo["loading_site"],
			"sales_order": order1.name,
			"transport_quotation": quotation1.name,
		})
		job.append("sales_order_rate_snapshots", {"sales_order_rate_snapshot": foreign_snapshot.name})
		job.append("permitted_loading_points", {"loading_location": self.demo["loading_site"]})
		with self.assertRaisesRegex(frappe.ValidationError, "is not on its Sales Order"):
			job.insert()

	def test_cancelled_open_job_allows_reconversion(self):
		quotation = self.make_approved_quotation()
		order = frappe.get_doc("Transport Sales Order", create_quotation_transport_sales_order(quotation.name))
		order.submit()

		job_name = create_transport_jobs(order.name)[0]
		self.assertEqual(frappe.db.get_value("Transport Sales Order", order.name, "status"), "Converted")

		# Cancel job
		job = frappe.get_doc("Transport Job", job_name)
		job.status = "Cancelled"
		job.save()

		order.reload()
		order.set_conversion_status()
		self.assertEqual(order.status, "Submitted")

		# Reconversion now succeeds
		new_jobs = create_transport_jobs(order.name)
		self.assertEqual(len(new_jobs), 1)
		self.assertNotEqual(new_jobs[0], job_name)

	def test_open_order_job_conversion_is_duplicate_safe(self):
		quotation = self.make_approved_quotation()
		order = frappe.get_doc(
			"Transport Sales Order",
			create_quotation_transport_sales_order(quotation.name),
		)
		order.submit()
		first_result = create_transport_jobs(order.name)
		with self.assertRaises(frappe.ValidationError):
			create_transport_jobs(order.name)
		self.assertEqual(
			frappe.db.count("Transport Job", {"sales_order": order.name, "quantity_mode": "Open"}),
			1,
		)
		self.assertEqual(len(first_result), 1)

	def test_multi_loading_stops_create_one_job_with_primary_loading_site(self):
		self.make_rate(rate=20)
		second_loading = self.make_loading_location()
		doc = self.make_sales_order(row={"manual_rate_override": 1, "rate": 30})
		doc.append("loading_stops", {
			"item_idx": 1,
			"loading_location": self.demo["loading_site"],
			"planned_quantity": 600,
			"notes": "First loading point",
		})
		doc.append("loading_stops", {
			"item_idx": 1,
			"loading_location": second_loading,
			"planned_quantity": 400,
			"notes": "Second loading point",
		})
		doc.save()
		doc.submit()

		jobs = create_transport_jobs(doc.name)
		self.assertEqual(len(jobs), 1)
		job = frappe.get_doc("Transport Job", jobs[0])
		self.assertEqual(job.loading_site, self.demo["loading_site"])
		self.assertEqual(job.requested_quantity, 1000)
		self.assertEqual(job.agreed_rate, 30)
		self.assertEqual(len(job.loading_stops), 2)
		self.assertEqual(job.loading_stops[0].loading_location, self.demo["loading_site"])
		self.assertEqual(job.loading_stops[0].planned_quantity, 600)
		self.assertEqual(job.loading_stops[1].loading_location, second_loading)
		self.assertEqual(job.loading_stops[1].planned_quantity, 400)

	def test_loading_stop_quantities_must_equal_item_quantity(self):
		doc = self.make_sales_order(row={"manual_rate_override": 1, "rate": 30})
		doc.append("loading_stops", {
			"item_idx": 1,
			"loading_location": self.demo["loading_site"],
			"planned_quantity": 999,
		})
		with self.assertRaisesRegex(frappe.ValidationError, "loading stop quantities must equal"):
			doc.save()

	def test_transport_job_receives_manual_agreed_rate_and_ordered_amount(self):
		doc = self.make_sales_order(submit=True, row={"manual_rate_override": 1, "rate": 45})
		job = frappe.get_doc("Transport Job", create_transport_jobs(doc.name)[0])
		self.assertEqual(job.agreed_rate, 45)
		self.assertEqual(job.ordered_amount, 45000)

	def test_draft_sales_order_cannot_create_transport_job(self):
		self.make_rate()
		doc = self.make_sales_order()
		with self.assertRaises(frappe.ValidationError):
			create_transport_jobs(doc.name)

	def test_two_selected_rows_create_two_transport_jobs_and_statuses(self):
		self.make_rate(rate=20)
		doc = self.make_sales_order()
		doc.append("items", {
			"material": self.demo["material"],
			"quantity": 500,
			"uom": "TON",
			"loading_location": self.demo["loading_site"],
			"unloading_location": self.demo["offloading_site"],
		})
		doc.save()
		doc.submit()
		first_row, second_row = doc.items

		jobs = create_transport_jobs(doc.name, [first_row.name])
		self.assertEqual(len(jobs), 1)
		self.assertEqual(frappe.db.get_value("Transport Sales Order", doc.name, "status"), "Partially Converted")

		jobs = create_transport_jobs(doc.name, [second_row.name])
		self.assertEqual(len(jobs), 1)
		self.assertEqual(frappe.db.get_value("Transport Sales Order", doc.name, "status"), "Converted")
		self.assertEqual(
			frappe.db.count("Transport Job", {"sales_order": doc.name}),
			2,
		)

	def test_duplicate_conversion_is_blocked(self):
		self.make_rate()
		doc = self.make_sales_order(submit=True)
		create_transport_jobs(doc.name)
		with self.assertRaises(frappe.ValidationError):
			create_transport_jobs(doc.name)
		self.assertEqual(frappe.db.count("Transport Job", {"sales_order": doc.name}), 1)

	def test_cancellation_with_active_linked_transport_job_is_blocked(self):
		self.make_rate()
		doc = self.make_sales_order(submit=True)
		create_transport_jobs(doc.name)
		with self.assertRaises(frappe.ValidationError):
			doc.cancel()

	def test_transport_job_quantity_progress_uses_supported_trip_quantities(self):
		material = self.demo["material"]
		truck = self.make_truck()
		self.make_rate(material=material)
		doc = self.make_sales_order(submit=True, row={"material": material})
		job_name = create_transport_jobs(doc.name)[0]
		driver_suffix = frappe.generate_hash(length=8)
		test_driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"TMS Job Progress Test Driver {driver_suffix}",
			"status": "Active",
			"cell_number": f"TMS-JP-{driver_suffix}",
		}).insert(ignore_permissions=True)
		trip = frappe.new_doc("Transport Trip")
		trip.update({
			"transport_job": job_name,
			"execution_source": "OWN",
			"trip_date": "2026-09-16",
			"vehicle": truck.name,
			"driver": test_driver.name,
			"loading_site": self.demo["loading_site"],
			"unloading_site": self.demo["offloading_site"],
			"material": material,
			"planned_quantity": 100,
			"actual_quantity": 90,
			"uom": "TON",
		})
		trip.insert()
		job = frappe.get_doc("Transport Job", job_name)
		self.assertEqual(job.assigned_quantity, 100)
		self.assertEqual(job.loaded_quantity, 0)
		self.assertEqual(job.delivered_quantity, 0)
		self.assertEqual(job.remaining_quantity, 1000)

	def test_sales_order_rbac(self):
		trip_user = self.make_user("TMS Trip Data Entry")
		expense_user = self.make_user("TMS + Expense Data Entry")
		manager_user = self.make_user("Transport Manager")
		admin_user = self.make_user("Transport Admin")

		self.assertTrue(frappe.has_permission("Transport Sales Order", "read", user=trip_user))
		self.assertFalse(frappe.has_permission("Transport Sales Order", "create", user=trip_user))
		self.assertTrue(frappe.has_permission("Transport Sales Order", "read", user=expense_user))
		self.assertFalse(frappe.has_permission("Transport Rate", "write", user=expense_user))

		for user in (manager_user, admin_user):
			self.assertTrue(frappe.has_permission("Transport Sales Order", "create", user=user))
			self.assertTrue(frappe.has_permission("Transport Sales Order", "submit", user=user))
			self.assertTrue(frappe.has_permission("Transport Rate", "create", user=user))
			self.assertTrue(frappe.has_permission("Transport Rate", "write", user=user))

	def test_area_zone_derived_from_rate_loading_location(self):
		quotation = self.make_approved_quotation()
		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		self.assertEqual(order.area_zone, "North Zone")
		self.assertEqual(order.order_mode, "Quotation-backed Open")
		self.assertTrue(len(order.rate_snapshots) > 0)

	def test_quotation_conversion_by_area_zone(self):
		quotation = self.make_approved_quotation(multi_area=True)
		north_so = create_quotation_transport_sales_order(quotation.name, area_zone="North Zone")
		south_so = create_quotation_transport_sales_order(quotation.name, area_zone="South Zone")

		doc_north = frappe.get_doc("Transport Sales Order", north_so)
		doc_south = frappe.get_doc("Transport Sales Order", south_so)

		self.assertEqual(doc_north.area_zone, "North Zone")
		self.assertEqual(doc_south.area_zone, "South Zone")

		# Check all snapshots in north belong to North Zone
		loc_names_north = [s.loading_location for s in doc_north.rate_snapshots]
		areas_north = set(frappe.get_all("Transport Location", filters={"name": ["in", loc_names_north]}, pluck="area_zone"))
		self.assertEqual(areas_north, {"North Zone"})

		# Check all snapshots in south belong to South Zone
		loc_names_south = [s.loading_location for s in doc_south.rate_snapshots]
		areas_south = set(frappe.get_all("Transport Location", filters={"name": ["in", loc_names_south]}, pluck="area_zone"))
		self.assertEqual(areas_south, {"South Zone"})

	def test_quotation_order_rejects_mixed_areas(self):
		quotation = self.make_approved_quotation(multi_area=True)
		# create_quotation_transport_sales_order without area_zone should reject multi-area
		with self.assertRaisesRegex(frappe.ValidationError, "rates across multiple geographical areas"):
			create_quotation_transport_sales_order(quotation.name)

		# Direct doc creation with mixed areas should also reject in validate_quotation_order
		order = frappe.new_doc("Transport Sales Order")
		order.update({
			"order_mode": "Quotation-backed Open",
			"transport_quotation": quotation.name,
			"customer": quotation.customer,
			"currency": "AED",
		})
		for rate in quotation.rates:
			order.append("rate_snapshots", {
				"source_quotation_rate": rate.name,
				"material": rate.material,
				"loading_location": rate.loading_location,
				"unloading_location": rate.unloading_location,
				"effective_from": rate.effective_from,
				"effective_to": rate.effective_to,
				"currency": quotation.currency,
				"rate": rate.rate,
			})
		with self.assertRaisesRegex(frappe.ValidationError, "selected rates span multiple areas"):
			order.insert()

	def test_quotation_order_rejects_missing_area_zone(self):
		blank_loc = self.make_loading_location(area_zone="")
		quotation = self.make_approved_quotation(approved=False)
		# Add a rate with blank area loading location
		quotation.append("locations", {
			"material": self.demo["material"],
			"location_role": "Loading",
			"location": blank_loc,
		})
		quotation.append("rates", {
			"material": self.demo["material"],
			"loading_location": blank_loc,
			"unloading_location": self.demo["offloading_site"],
			"rate": 30,
			"effective_from": "2026-01-01",
			"effective_to": "2027-12-31",
		})
		quotation.submit()

		with self.assertRaisesRegex(frappe.ValidationError, "does not have a geographical area"):
			create_quotation_transport_sales_order(quotation.name)

	def test_duplicate_quotation_rate_conversion_blocked(self):
		quotation = self.make_approved_quotation()
		create_quotation_transport_sales_order(quotation.name)

		with self.assertRaisesRegex(frappe.ValidationError, "already been converted in active Sales Order"):
			create_quotation_transport_sales_order(quotation.name)

	def test_cancelled_sales_order_allows_reconversion(self):
		quotation = self.make_approved_quotation()
		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()
		order.cancel()

		# Now reconversion should succeed
		new_order_name = create_quotation_transport_sales_order(quotation.name)
		self.assertTrue(new_order_name)
		self.assertNotEqual(order_name, new_order_name)

	def test_get_quotation_sales_order_summary(self):
		quotation = self.make_approved_quotation(multi_area=True)
		summary = get_quotation_sales_order_summary(quotation.name)
		self.assertEqual(summary["total_areas"], 2)
		self.assertEqual(summary["converted_areas"], 0)
		self.assertTrue(summary["has_unconverted_areas"])

		# Convert North Zone
		north_so = create_quotation_transport_sales_order(quotation.name, area_zone="North Zone")
		summary2 = get_quotation_sales_order_summary(quotation.name)
		self.assertEqual(summary2["converted_areas"], 1)
		self.assertTrue(summary2["has_unconverted_areas"])
		north_area = next(a for a in summary2["areas"] if a["area_zone"] == "North Zone")
		self.assertTrue(north_area["is_fully_converted"])
		self.assertEqual(len(north_area["sales_orders"]), 1)
		self.assertEqual(north_area["sales_orders"][0]["sales_order"], north_so)

		# Convert South Zone
		south_so = create_quotation_transport_sales_order(quotation.name, area_zone="South Zone")
		summary3 = get_quotation_sales_order_summary(quotation.name)
		self.assertEqual(summary3["converted_areas"], 2)
		self.assertFalse(summary3["has_unconverted_areas"])

	def test_unauthorized_conversion_attempt_raises_permission_error(self):
		quotation = self.make_approved_quotation()
		trip_user = self.make_user("TMS Trip Data Entry")
		frappe.set_user(trip_user)

		with self.assertRaises(frappe.PermissionError):
			create_quotation_transport_sales_order(quotation.name)

	def test_unapproved_quotation_conversion_blocked(self):
		quotation = self.make_approved_quotation(approved=False)
		with self.assertRaisesRegex(frappe.ValidationError, "Only an approved, submitted Transport Quotation"):
			create_quotation_transport_sales_order(quotation.name)

	def test_fixed_quantity_sales_order_preserves_behavior(self):
		self.make_rate()
		order = self.make_sales_order(submit=True)
		self.assertEqual(order.order_mode, "Fixed Quantity")
		self.assertEqual(order.status, "Submitted")


class TestPhase2CTripExecution(unittest.TestCase):
	make_truck = TestTransportSalesOrder.make_truck
	make_loading_location = TestTransportSalesOrder.make_loading_location
	make_destination = TestTransportSalesOrder.make_destination
	make_loading_paper = TestTransportSalesOrder.make_loading_paper
	make_approved_quotation = TestTransportSalesOrder.make_approved_quotation

	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_trip", force=True)
		reload_doc("transport_management", "doctype", "transport_trip_document", force=True)

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("phase2c_trip_execution_test")
		self.demo = setup_demo_data()
		driver_suffix = frappe.generate_hash(length=8)
		test_driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"TMS Phase 2C Test Driver {driver_suffix}",
			"status": "Active",
			"cell_number": f"TMS-P2C-{driver_suffix}",
		}).insert(ignore_permissions=True)
		self.demo["driver"] = test_driver.name

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="phase2c_trip_execution_test")

	def create_open_order_and_job(self, **quotation_values):
		quotation = self.make_approved_quotation(**quotation_values)
		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()
		job = frappe.get_doc("Transport Job", create_transport_jobs(order.name)[0])
		return quotation, order, job

	def create_assigned_trip(self, job, planned_quantity=None):
		return create_assigned_transport_trip(
			transport_job=job.name,
			vehicle=self.make_truck().name,
			driver=self.demo["driver"],
			material=job.material,
			loading_site=job.loading_site,
			unloading_site=job.unloading_site,
			trip_date=today(),
			planned_quantity=planned_quantity,
		)

	def make_offloading_paper(self, trip, **values):
		document = frappe.new_doc("Transport Trip Document")
		document.update({
			"transport_trip": trip,
			"document_type": "OFFLOADING_PAPER",
			"file": "/files/test-offloading-paper.pdf",
			"uploaded_by_driver": self.demo["driver"],
		})
		document.update(values)
		document.insert(ignore_permissions=True)
		return document

	def make_loading_paper(self, trip, **values):
		document = frappe.new_doc("Transport Trip Document")
		document.update({
			"transport_trip": trip,
			"document_type": "LOADING_PAPER",
			"file": "/files/test-loading-paper.pdf",
			"uploaded_by_driver": self.demo["driver"],
		})
		document.update(values)
		document.insert(ignore_permissions=True)
		return document

	def move_open_trip_to_delivered(self, trip_name):
		trip = frappe.get_doc("Transport Trip", trip_name)
		trip.status = "IN_TRANSIT"
		trip.driver_started_at = now_datetime()
		trip.flags.driver_portal_start_trip = True
		trip.save()

		trip = frappe.get_doc("Transport Trip", trip_name)
		trip.status = "DELIVERED"
		trip.driver_delivered_at = now_datetime()
		trip.delivery_datetime = now_datetime()
		trip.delivered_quantity = trip.loaded_quantity
		trip.save()

	def make_test_driver(self):
		driver_suffix = frappe.generate_hash(length=8)
		return frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"TMS Phase 2C Test Driver {driver_suffix}",
			"status": "Active",
			"cell_number": f"TMS-P2C-{driver_suffix}",
		}).insert(ignore_permissions=True).name

	def test_open_job_does_not_reject_trip_quantities_above_order_estimate(self):
		_, _, job = self.create_open_order_and_job(estimated_quantity=50, estimated_trips=1)
		trip_names = []
		for planned_quantity in (None, 100):
			with self.subTest(planned_quantity=planned_quantity):
				if trip_names:
					active_trip = frappe.get_doc("Transport Trip", trip_names[-1])
					active_trip.status = "CANCELLED"
					active_trip.save()
				trip = self.create_assigned_trip(job, planned_quantity)
				trip_names.append(trip["name"])

		self.assertEqual(len(trip_names), 2)
		self.assertEqual(
			[frappe.db.get_value("Transport Trip", name, "planned_quantity") for name in trip_names],
			[0, 100],
		)
		self.assertEqual(frappe.db.get_value("Transport Job", job.name, "requested_quantity"), 0)
		self.assertFalse(frappe.db.get_value("Transport Job", job.name, "estimated_quantity"))

	def test_open_job_trips_are_not_exposed_to_fixed_rate_billing(self):
		_, order, job = self.create_open_order_and_job()
		self.create_assigned_trip(job)

		self.assertEqual(evaluate_billing_readiness(job.name), "Not Ready")
		self.assertEqual(evaluate_sales_order_billing_status(order.name), "Not Ready")
		self.assertEqual(get_billable_trips(job), [])
		self.assertEqual(get_sales_order_billable_trips(order.name), [])
		self.assertEqual(get_customer_billable_trips(order.customer, today(), today()), [])

	def test_dispatch_assignment_enforces_driver_availability_and_permitted_loading_points(self):
		_, _, job = self.create_open_order_and_job()
		with patch("frappe.db.sql", wraps=frappe.db.sql) as execute_sql:
			first_trip = self.create_assigned_trip(job)
		lock_queries = [
			str(call.args[0]).lower()
			for call in execute_sql.call_args_list
			if "for update" in str(call.args[0]).lower()
		]
		self.assertTrue(any("`tabtruck`" in query for query in lock_queries))
		self.assertTrue(any("`tabtruck driver`" in query for query in lock_queries))

		with self.assertRaisesRegex(frappe.ValidationError, "already assigned to active Trip"):
			self.create_assigned_trip(job)

		with self.assertRaisesRegex(frappe.ValidationError, "Vehicle .* already assigned to active Trip"):
			create_assigned_transport_trip(
				transport_job=job.name,
				vehicle=first_trip["vehicle"],
				driver=self.make_test_driver(),
				material=job.material,
				loading_site=job.loading_site,
				unloading_site=job.unloading_site,
				trip_date=today(),
			)

		trip_doc = frappe.get_doc("Transport Trip", first_trip["name"])
		trip_doc.status = "CANCELLED"
		trip_doc.save()

		unpermitted_loading = self.make_loading_location()
		with self.assertRaisesRegex(frappe.ValidationError, "permitted loading points"):
			create_assigned_transport_trip(
				transport_job=job.name,
				vehicle=self.make_truck().name,
				driver=self.demo["driver"],
				material=job.material,
				loading_site=unpermitted_loading,
				unloading_site=job.unloading_site,
				trip_date=today(),
			)

		reassigned_trip = self.create_assigned_trip(job)
		self.assertEqual(reassigned_trip["status"], "ASSIGNED")

	def test_verified_loading_facts_resolve_and_lock_approved_snapshot_by_loading_date(self):
		quotation, order, job = self.create_open_order_and_job(multiple_routes=True)
		trip = self.create_assigned_trip(job)
		actual_material = next(
			material.material for material in quotation.materials if material.material != job.material
		)
		document = self.make_loading_paper(trip["name"])
		verify_trip_loading_document(document.name, actual_material, job.loading_site, today(), 42.5)
		result = confirm_trip_loading(trip["name"], document.name)
		updated_trip = frappe.get_doc("Transport Trip", trip["name"])
		matching_snapshot = next(
			row
			for row in order.rate_snapshots
			if row.material == actual_material
			and row.loading_location == job.loading_site
			and row.unloading_location == job.unloading_site
			and getdate(row.effective_from) <= getdate(today()) <= getdate(row.effective_to)
		)

		self.assertEqual(result["status"], "LOADED")
		self.assertEqual(updated_trip.material, job.material)
		self.assertEqual(updated_trip.actual_material, actual_material)
		self.assertEqual(getdate(updated_trip.actual_loading_date), getdate(today()))
		self.assertEqual(updated_trip.loaded_quantity, 42.5)
		self.assertEqual(updated_trip.applied_rate_snapshot, matching_snapshot.name)
		self.assertEqual(updated_trip.applied_rate_per_ton, matching_snapshot.rate)
		self.assertEqual(updated_trip.applied_rate_currency, "AED")
		self.assertEqual(updated_trip.commercial_rate_status, "CONFIRMED")
		self.assertTrue(confirm_trip_loading(trip["name"], document.name)["already_confirmed"])

		approved_document = frappe.get_doc("Transport Trip Document", document.name)
		self.assertEqual(approved_document.verification_status, "APPROVED")
		self.assertEqual(approved_document.verified_by, frappe.session.user)
		self.assertTrue(approved_document.verified_at)
		approved_document.review_notes = "Unauthorized rewrite"
		with self.assertRaisesRegex(frappe.ValidationError, "audit details are immutable"):
			approved_document.save()

		updated_trip.actual_material = job.material
		with self.assertRaisesRegex(frappe.ValidationError, "can only be changed by the loading operation"):
			updated_trip.save()
		updated_trip = frappe.get_doc("Transport Trip", trip["name"])
		updated_trip.applied_rate_per_ton += 1
		with self.assertRaisesRegex(frappe.ValidationError, "can only be changed by the loading operation"):
			updated_trip.save()

	def test_loading_document_review_requires_authorization_audit_and_allows_reupload_after_rejection(self):
		_, _, job = self.create_open_order_and_job()
		trip = self.create_assigned_trip(job)
		document = self.make_loading_paper(trip["name"])
		document.verified_material = job.material
		with self.assertRaisesRegex(frappe.ValidationError, "cannot contain verified facts"):
			document.save()

		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				verify_trip_loading_document(
					document.name,
					job.material,
					job.loading_site,
					today(),
					40,
				)
			with self.assertRaises(frappe.PermissionError):
				reject_trip_loading_document(document.name, "Not a reviewer")
		finally:
			frappe.set_user("Administrator")

		reject_trip_loading_document(document.name, "Unreadable loading paper")
		rejected = frappe.get_doc("Transport Trip Document", document.name)
		self.assertEqual(rejected.verification_status, "REJECTED")
		self.assertEqual(rejected.verified_by, frappe.session.user)
		self.assertTrue(rejected.verified_at)
		replacement = self.make_loading_paper(
			trip["name"],
			file="/files/replacement-loading-paper.pdf",
		)
		self.assertEqual(replacement.verification_status, "PENDING_REVIEW")

	def test_verified_loading_without_snapshot_route_is_marked_rate_blocked(self):
		_, _, job = self.create_open_order_and_job()
		trip = self.create_assigned_trip(job)
		uncovered_loading = self.make_loading_location()
		document = self.make_loading_paper(trip["name"])
		verify_trip_loading_document(document.name, job.material, uncovered_loading, today(), 42.5)

		result = confirm_trip_loading(trip["name"], document.name)
		updated_trip = frappe.get_doc("Transport Trip", trip["name"])
		self.assertEqual(result["status"], "LOADED")
		self.assertEqual(updated_trip.commercial_rate_status, "RATE_BLOCKED")
		self.assertIn("No approved quotation rate covers", updated_trip.rate_block_reason)
		self.assertFalse(updated_trip.applied_rate_snapshot)
		self.assertFalse(updated_trip.rate_locked_at)

	def test_open_billing_uses_verified_delivery_quantity_and_locked_rate(self):
		_, order, job = self.create_open_order_and_job()
		trip_ref = self.create_assigned_trip(job)
		loading_paper = self.make_loading_paper(trip_ref["name"])
		verify_trip_loading_document(
			loading_paper.name,
			job.material,
			job.loading_site,
			today(),
			42.5,
		)
		confirm_trip_loading(trip_ref["name"], loading_paper.name)
		self.move_open_trip_to_delivered(trip_ref["name"])

		offloading_paper = self.make_offloading_paper(trip_ref["name"])
		self.assertEqual(get_open_order_billable_trips(sales_order=order.name), [])
		verify_trip_delivery_document(offloading_paper.name, today(), 35)

		trip = frappe.get_doc("Transport Trip", trip_ref["name"])
		trip.status = "POD_RECEIVED"
		trip.pod_attachment = "/files/test-pod.pdf"
		trip.save()
		trip = frappe.get_doc("Transport Trip", trip_ref["name"])
		trip.status = "CLOSED"
		trip.save()

		billable = get_open_order_billable_trips(sales_order=order.name, from_date=today(), to_date=today())
		self.assertEqual([row.name for row in billable], [trip_ref["name"]])
		self.assertEqual(billable[0].delivered_quantity, 35)
		self.assertEqual(billable[0].agreed_rate, trip.applied_rate_per_ton)
		self.assertEqual(evaluate_billing_readiness(job.name), "Ready for Billing")
		self.assertEqual(evaluate_sales_order_billing_status(order.name), "Ready for Billing")

		groups = group_sales_order_invoice_trips(billable)
		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0]["qty"], 35)
		self.assertEqual(groups[0]["rate"], trip.applied_rate_per_ton)

		invoice = frappe._dict({
			"currency": "AED",
			"items": [
				frappe._dict({
					"tms_material": trip.actual_material,
					"tms_loading_location": trip.actual_loading_location,
					"tms_unloading_location": trip.unloading_site,
					"qty": 35,
					"rate": trip.applied_rate_per_ton,
				})
			],
		})
		validate_invoice_trip_item_snapshot(invoice, [trip.name])
		invoice.get("items")[0].qty = trip.loaded_quantity
		with self.assertRaisesRegex(frappe.ValidationError, "must match the selected Trips"):
			validate_invoice_trip_item_snapshot(invoice, [trip.name])

		draft_invoice = frappe._dict({
			"name": "SINV-P2D-OPEN-DRAFT",
			"docstatus": 0,
			"tms_transport_trips": frappe.as_json([trip.name]),
		})
		sync_direct_transport_invoice_lifecycle(draft_invoice)
		with self.assertRaisesRegex(frappe.ValidationError, "already included in Sales Invoice"):
			validate_invoice_trips_not_already_billed([trip.name])
		self.assertEqual(get_open_order_billable_trips(sales_order=order.name), [])
		draft_invoice.docstatus = 2
		sync_direct_transport_invoice_lifecycle(draft_invoice, method="on_cancel")
		self.assertEqual([row.name for row in get_open_order_billable_trips(sales_order=order.name)], [trip.name])

		approved = frappe.get_doc("Transport Trip Document", offloading_paper.name)
		approved.review_notes = "Unauthorized review change"
		with self.assertRaisesRegex(frappe.ValidationError, "audit details are immutable"):
			approved.save()

	def test_offloading_paper_review_requires_authorization_and_allows_reupload(self):
		_, _, job = self.create_open_order_and_job()
		trip_ref = self.create_assigned_trip(job)
		loading_paper = self.make_loading_paper(trip_ref["name"])
		verify_trip_loading_document(loading_paper.name, job.material, job.loading_site, today(), 42.5)
		confirm_trip_loading(trip_ref["name"], loading_paper.name)
		self.move_open_trip_to_delivered(trip_ref["name"])
		document = self.make_offloading_paper(trip_ref["name"])

		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				verify_trip_delivery_document(document.name, today(), 35)
		finally:
			frappe.set_user("Administrator")

		reject_trip_delivery_document(document.name, "Unreadable offloading paper")
		replacement = self.make_offloading_paper(trip_ref["name"])
		result = verify_trip_delivery_document(replacement.name, today(), 35)
		self.assertEqual(result["verification_status"], "APPROVED")
		self.assertEqual(result["verified_delivered_quantity"], 35)
		self.assertEqual(
			frappe.db.get_value("Transport Trip", trip_ref["name"], "delivered_quantity"),
			35,
		)

	def test_open_trip_route_options_and_defaults(self):
		quotation = self.make_approved_quotation(multiple_routes=True)
		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()
		job_names = create_transport_jobs(order.name)
		job = frappe.get_doc("Transport Job", job_names[0])

		defaults = get_defaults_from_transport_job(job.name)
		self.assertEqual(defaults["quantity_mode"], "Open")
		self.assertEqual(defaults["material"], job.material)
		self.assertTrue(len(defaults["permitted_loading_points"]) >= 1)
		self.assertTrue(len(defaults["permitted_destinations"]) >= 1)
		self.assertTrue(len(defaults["permitted_routes"]) >= 1)

		opts = get_trip_route_options(job.name)
		self.assertEqual(opts["quantity_mode"], "Open")
		self.assertEqual(opts["material"], job.material)
		self.assertEqual(set(opts["loading_points"]), set(defaults["permitted_loading_points"]))
		self.assertEqual(set(opts["destinations"]), set(defaults["permitted_destinations"]))

		first_loading = opts["loading_points"][0]
		filtered_opts = get_trip_route_options(job.name, loading_site=first_loading)
		expected_destinations = {
			r["unloading_location"] for r in opts["routes"] if r["loading_location"] == first_loading
		}
		self.assertEqual(set(filtered_opts["destinations"]), expected_destinations)

	def test_open_trip_route_pair_validation_and_rejection(self):
		material = self.demo["material"]
		l1 = self.make_loading_location(area_zone="Test Area Zone")
		l2 = self.make_loading_location(area_zone="Test Area Zone")
		d1 = self.make_destination(area_zone="Dest Area 1")
		d2 = self.make_destination(area_zone="Dest Area 2")
		unrelated_loading = self.make_loading_location(area_zone="Other Area")
		unrelated_dest = self.make_destination(area_zone="Other Dest")

		quotation = frappe.new_doc("Transport Quotation")
		quotation.update({
			"quotation_date": today(),
			"valid_until": today(),
			"service_period_from": "2026-01-01",
			"service_period_to": "2027-12-31",
			"customer": self.demo["customer"],
			"currency": "AED",
			"customer_approval_date": today(),
		})
		quotation.append("materials", {"material": material})
		quotation.append("locations", {"material": material, "location_role": "Loading", "location": l1})
		quotation.append("locations", {"material": material, "location_role": "Loading", "location": l2})
		quotation.append("locations", {"material": material, "location_role": "Destination", "location": d1})
		quotation.append("locations", {"material": material, "location_role": "Destination", "location": d2})
		# Authorized pairs: (l1, d1) and (l2, d2) ONLY
		quotation.append("rates", {
			"material": material,
			"loading_location": l1,
			"unloading_location": d1,
			"rate": 30,
			"effective_from": "2026-01-01",
			"effective_to": "2027-12-31",
		})
		quotation.append("rates", {
			"material": material,
			"loading_location": l2,
			"unloading_location": d2,
			"rate": 45,
			"effective_from": "2026-01-01",
			"effective_to": "2027-12-31",
		})
		quotation.insert(ignore_permissions=True)
		quotation.status = "Approved"
		quotation.save(ignore_permissions=True)
		quotation.submit()

		order_name = create_quotation_transport_sales_order(quotation.name)
		order = frappe.get_doc("Transport Sales Order", order_name)
		order.submit()
		job = frappe.get_doc("Transport Job", create_transport_jobs(order.name)[0])

		truck1 = self.make_truck()
		driver1 = self.make_test_driver()

		# Case 1: Valid authorized route (l1, d1) succeeds
		trip1 = create_assigned_transport_trip(
			transport_job=job.name,
			vehicle=truck1.name,
			driver=driver1,
			material=material,
			loading_site=l1,
			unloading_site=d1,
			trip_date=today(),
		)
		self.assertEqual(trip1["status"], "ASSIGNED")
		self.assertEqual(frappe.db.get_value("Transport Trip", trip1["name"], "unloading_site"), d1)

		# Case 2: Unpermitted loading point rejected
		truck2 = self.make_truck()
		driver2 = self.make_test_driver()
		with self.assertRaisesRegex(frappe.ValidationError, "permitted loading points"):
			create_assigned_transport_trip(
				transport_job=job.name,
				vehicle=truck2.name,
				driver=driver2,
				material=material,
				loading_site=unrelated_loading,
				unloading_site=d1,
				trip_date=today(),
			)

		# Case 3: Unpermitted destination rejected
		with self.assertRaisesRegex(frappe.ValidationError, "not permitted for Transport Job"):
			create_assigned_transport_trip(
				transport_job=job.name,
				vehicle=truck2.name,
				driver=driver2,
				material=material,
				loading_site=l1,
				unloading_site=unrelated_dest,
				trip_date=today(),
			)

		# Case 4: Individually permitted loading point (l1) and destination (d2) that do not form an authorized route pair
		with self.assertRaisesRegex(frappe.ValidationError, "is not authorized for Transport Job"):
			create_assigned_transport_trip(
				transport_job=job.name,
				vehicle=truck2.name,
				driver=driver2,
				material=material,
				loading_site=l1,
				unloading_site=d2,
				trip_date=today(),
			)

		# Case 5: The other authorized pair (l2, d2) succeeds under the same job!
		trip2 = create_assigned_transport_trip(
			transport_job=job.name,
			vehicle=truck2.name,
			driver=driver2,
			material=material,
			loading_site=l2,
			unloading_site=d2,
			trip_date=today(),
		)
		self.assertEqual(trip2["status"], "ASSIGNED")
		self.assertEqual(frappe.db.get_value("Transport Trip", trip2["name"], "unloading_site"), d2)

		# Verify both trips exist for the same job with different destinations
		self.assertEqual(
			frappe.db.get_value("Transport Trip", trip1["name"], "unloading_site"),
			d1,
		)
		self.assertEqual(
			frappe.db.get_value("Transport Trip", trip2["name"], "unloading_site"),
			d2,
		)
