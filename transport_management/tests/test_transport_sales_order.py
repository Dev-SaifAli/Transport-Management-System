"""Tests for TMS Sales Order foundation and conversion to Transport Job."""

import unittest

import frappe
from frappe.modules import reload_doc

from transport_management.demo import setup_demo_data
from transport_management.rbac import ensure_tms_rbac
from transport_management.transport_management.doctype.transport_sales_order.transport_sales_order import (
	create_transport_jobs,
	ensure_ton_uom,
	get_transport_rate,
)


class TestTransportSalesOrder(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_sales_order_item", force=True)
		reload_doc("transport_management", "doctype", "transport_sales_order", force=True)
		reload_doc("transport_management", "doctype", "transport_rate", force=True)
		reload_doc("transport_management", "doctype", "transport_job", force=True)
		reload_doc("transport_management", "doctype", "transport_trip", force=True)
		ensure_ton_uom()
		ensure_tms_rbac()

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

	def make_sales_order(self, submit=False, **values):
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
		doc.insert()
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

	def test_naming_series_and_customer_link_use_erpnext_customer(self):
		self.make_rate()
		doc = self.make_sales_order()
		self.assertRegex(doc.name, r"^TSO-\d{4}-\d{5}$")
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
		material = "3/4 AGREEGAT(10MM-20MM)"
		frappe.db.set_value("Truck", self.demo["vehicle"], "vehicle_type", "TIPPER")
		self.make_rate(material=material)
		doc = self.make_sales_order(submit=True, row={"material": material})
		job_name = create_transport_jobs(doc.name)[0]
		frappe.db.delete("Transport Trip", {"transport_job": job_name})
		trip = frappe.new_doc("Transport Trip")
		trip.update({
			"transport_job": job_name,
			"execution_source": "OWN",
			"trip_date": "2026-09-16",
			"vehicle": self.demo["vehicle"],
			"driver": self.demo["driver"],
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
