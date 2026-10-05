"""Tests for TMS traceability fields on ERPNext Purchase Invoice rows."""

import unittest

import frappe
from frappe.modules import reload_doc

from transport_management.tms_billing_setup import ensure_tms_billing_setup
from transport_management.tms_expense_traceability import (
	get_purchase_invoice_item_tms_defaults,
	normalize_purchase_invoice_tms_references,
)


class TestPurchaseInvoiceTMSTraceability(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_job", force=True)
		reload_doc("transport_management", "doctype", "transport_trip", force=True)

	def setUp(self):
		frappe.db.savepoint("purchase_invoice_tms_traceability")
		ensure_tms_billing_setup()
		self.fixture = self.make_fixture()

	def tearDown(self):
		frappe.db.rollback(save_point="purchase_invoice_tms_traceability")

	def make_fixture(self):
		suffix = frappe.generate_hash(length=8)
		country = frappe.db.get_value("Country", "United Arab Emirates") or frappe.db.get_value("Country", {})
		self.ensure_uom("TON")
		truck_type = self.ensure_truck_type("TIPPER")
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": f"TMS PI Trace Customer {suffix}",
			"customer_type": "Company",
		}).insert(ignore_permissions=True)
		supplier = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": f"TMS PI Trace Transporter {suffix}",
			"supplier_type": "Company",
			"is_transporter": 1,
			"transporter_status": "Active",
		}).insert(ignore_permissions=True)
		material = frappe.get_doc({
			"doctype": "Cargo Types",
			"cargo_name": f"TMS PI Trace Material {suffix}",
			"active": 1,
			"allowed_truck_types": [{"truck_type": truck_type}],
		}).insert(ignore_permissions=True)
		loading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"TMS PI Trace Loading {suffix}",
			"country": country,
			"location_usage": "Loading",
			"location_type": "Plant",
			"active": 1,
		}).insert(ignore_permissions=True)
		unloading_site = frappe.get_doc({
			"doctype": "Transport Location",
			"location": f"TMS PI Trace Unloading {suffix}",
			"country": country,
			"location_usage": "Unloading",
			"location_type": "Customer Site",
			"customer": customer.name,
			"active": 1,
		}).insert(ignore_permissions=True)
		driver = frappe.get_doc({
			"doctype": "Truck Driver",
			"full_name": f"TMS PI Trace Driver {suffix}",
			"status": "Active",
			"cell_number": f"TRACE-{suffix}",
		}).insert(ignore_permissions=True)
		truck = frappe.get_doc({
			"doctype": "Truck",
			"truck_number": f"TMS-TRACE-{suffix}",
			"license_plate": f"TMS-TRACE-{suffix}",
			"vehicle_type": truck_type,
			"ownership_type": "OWN",
			"status": "Idle",
			"disabled": 0,
		}).insert(ignore_permissions=True)
		hired_vehicle = frappe.get_doc({
			"doctype": "Hired Vehicle",
			"transporter": supplier.name,
			"plate_number": f"HV-TRACE-{suffix}",
			"vehicle_type": truck_type,
			"active": 1,
		}).insert(ignore_permissions=True)
		return {
			"customer": customer.name,
			"transporter_supplier": supplier.name,
			"hired_vehicle": hired_vehicle.name,
			"loading_site": loading_site.name,
			"offloading_site": unloading_site.name,
			"material": material.name,
			"driver": driver.name,
			"vehicle": truck.name,
		}

	def ensure_uom(self, uom):
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc({"doctype": "UOM", "uom_name": uom, "enabled": 1}).insert(ignore_permissions=True)

	def ensure_truck_type(self, truck_type):
		if not frappe.db.exists("Truck Type", truck_type):
			frappe.get_doc({"doctype": "Truck Type", "truck_type": truck_type}).insert(ignore_permissions=True)
		return truck_type

	def make_sales_order(self):
		doc = frappe.new_doc("Transport Sales Order")
		doc.update({
			"posting_date": "2026-09-16",
			"customer": self.fixture["customer"],
			"items": [{
				"material": self.fixture["material"],
				"quantity": 10,
				"uom": "TON",
				"loading_location": self.fixture["loading_site"],
				"unloading_location": self.fixture["offloading_site"],
			}],
		})
		doc.insert(ignore_permissions=True)
		return doc

	def make_job(self, sales_order=None, **values):
		doc = frappe.new_doc("Transport Job")
		doc.update({
			"customer": self.fixture["customer"],
			"requested_date": "2026-09-16",
			"loading_site": self.fixture["loading_site"],
			"unloading_site": self.fixture["offloading_site"],
			"material": self.fixture["material"],
			"requested_quantity": 20,
			"uom": "TON",
			"sales_order": sales_order,
		})
		doc.update(values)
		doc.insert(ignore_permissions=True)
		return doc

	def make_trip(self, job, **values):
		doc = frappe.new_doc("Transport Trip")
		doc.update({
			"transport_job": job.name,
			"execution_source": "OWN",
			"trip_date": job.requested_date,
			"vehicle": self.fixture["vehicle"],
			"driver": self.fixture["driver"],
			"loading_site": job.loading_site,
			"unloading_site": job.unloading_site,
			"material": job.material,
			"planned_quantity": 10,
			"uom": "TON",
		})
		doc.update(values)
		doc.insert(ignore_permissions=True)
		return doc

	def make_purchase_invoice(self, rows):
		doc = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"items": rows,
		})
		return doc

	def test_purchase_invoice_item_custom_fields_are_installed(self):
		meta = frappe.get_meta("Purchase Invoice Item", cached=False)
		expected_fields = {
			"tms_transport_trip": ("Link", "Transport Trip"),
			"tms_transport_job": ("Link", "Transport Job"),
			"tms_transport_sales_order": ("Link", "Transport Sales Order"),
			"tms_truck": ("Link", "Truck"),
			"tms_hired_vehicle": ("Link", "Hired Vehicle"),
		}
		for fieldname, (fieldtype, options) in expected_fields.items():
			field = meta.get_field(fieldname)
			self.assertIsNotNone(field)
			self.assertEqual(field.fieldtype, fieldtype)
			self.assertEqual(field.options, options)
			self.assertFalse(field.reqd)

	def test_trip_derives_job_sales_order_and_owned_truck(self):
		sales_order = self.make_sales_order()
		job = self.make_job(sales_order=sales_order.name)
		trip = self.make_trip(job)
		doc = self.make_purchase_invoice([{"tms_transport_trip": trip.name}])

		normalize_purchase_invoice_tms_references(doc)
		row = doc.items[0]

		self.assertEqual(row.tms_transport_job, job.name)
		self.assertEqual(row.tms_transport_sales_order, sales_order.name)
		self.assertEqual(row.tms_truck, self.fixture["vehicle"])
		self.assertFalse(row.tms_hired_vehicle)

	def test_hired_trip_derives_hired_vehicle_without_truck(self):
		sales_order = self.make_sales_order()
		job = self.make_job(sales_order=sales_order.name)
		trip = self.make_trip(
			job,
			execution_source="HIRED",
			vehicle=None,
			driver=None,
			transporter=self.fixture["transporter_supplier"],
			hired_vehicle=self.fixture["hired_vehicle"],
		)
		doc = self.make_purchase_invoice([{"tms_transport_trip": trip.name, "tms_truck": self.fixture["vehicle"]}])

		normalize_purchase_invoice_tms_references(doc)
		row = doc.items[0]

		self.assertEqual(row.tms_transport_job, job.name)
		self.assertEqual(row.tms_transport_sales_order, sales_order.name)
		self.assertFalse(row.tms_truck)
		self.assertEqual(row.tms_hired_vehicle, self.fixture["hired_vehicle"])

	def test_trip_authoritatively_normalizes_conflicting_references(self):
		correct_sales_order = self.make_sales_order()
		wrong_sales_order = self.make_sales_order()
		correct_job = self.make_job(sales_order=correct_sales_order.name)
		wrong_job = self.make_job(sales_order=wrong_sales_order.name)
		trip = self.make_trip(correct_job)
		doc = self.make_purchase_invoice([{
			"tms_transport_trip": trip.name,
			"tms_transport_job": wrong_job.name,
			"tms_transport_sales_order": wrong_sales_order.name,
			"tms_hired_vehicle": self.fixture["hired_vehicle"],
		}])

		normalize_purchase_invoice_tms_references(doc)
		row = doc.items[0]

		self.assertEqual(row.tms_transport_job, correct_job.name)
		self.assertEqual(row.tms_transport_sales_order, correct_sales_order.name)
		self.assertEqual(row.tms_truck, self.fixture["vehicle"])
		self.assertFalse(row.tms_hired_vehicle)

	def test_job_only_expense_derives_sales_order(self):
		sales_order = self.make_sales_order()
		job = self.make_job(sales_order=sales_order.name)
		doc = self.make_purchase_invoice([{"tms_transport_job": job.name}])

		normalize_purchase_invoice_tms_references(doc)

		self.assertEqual(doc.items[0].tms_transport_sales_order, sales_order.name)

	def test_job_only_expense_rejects_conflicting_sales_order(self):
		correct_sales_order = self.make_sales_order()
		wrong_sales_order = self.make_sales_order()
		job = self.make_job(sales_order=correct_sales_order.name)
		doc = self.make_purchase_invoice([{
			"tms_transport_job": job.name,
			"tms_transport_sales_order": wrong_sales_order.name,
		}])

		with self.assertRaisesRegex(frappe.ValidationError, "belongs to Transport Sales Order"):
			normalize_purchase_invoice_tms_references(doc)

	def test_vehicle_only_and_empty_rows_remain_valid(self):
		doc = self.make_purchase_invoice([
			{"tms_truck": self.fixture["vehicle"]},
			{"tms_hired_vehicle": self.fixture["hired_vehicle"]},
			{},
		])

		normalize_purchase_invoice_tms_references(doc)

		self.assertEqual(doc.items[0].tms_truck, self.fixture["vehicle"])
		self.assertEqual(doc.items[1].tms_hired_vehicle, self.fixture["hired_vehicle"])
		self.assertFalse(doc.items[2].get("tms_transport_trip"))

	def test_multiple_rows_can_reference_different_trips(self):
		first_sales_order = self.make_sales_order()
		second_sales_order = self.make_sales_order()
		first_job = self.make_job(sales_order=first_sales_order.name)
		second_job = self.make_job(sales_order=second_sales_order.name)
		first_trip = self.make_trip(first_job)
		second_trip = self.make_trip(
			second_job,
			execution_source="HIRED",
			vehicle=None,
			driver=None,
			transporter=self.fixture["transporter_supplier"],
			hired_vehicle=self.fixture["hired_vehicle"],
		)
		doc = self.make_purchase_invoice([
			{"tms_transport_trip": first_trip.name},
			{"tms_transport_trip": second_trip.name},
		])

		normalize_purchase_invoice_tms_references(doc)

		self.assertEqual(doc.items[0].tms_transport_job, first_job.name)
		self.assertEqual(doc.items[0].tms_transport_sales_order, first_sales_order.name)
		self.assertEqual(doc.items[0].tms_truck, self.fixture["vehicle"])
		self.assertEqual(doc.items[1].tms_transport_job, second_job.name)
		self.assertEqual(doc.items[1].tms_transport_sales_order, second_sales_order.name)
		self.assertEqual(doc.items[1].tms_hired_vehicle, self.fixture["hired_vehicle"])

	def test_client_defaults_api_matches_server_derivation(self):
		sales_order = self.make_sales_order()
		job = self.make_job(sales_order=sales_order.name)
		trip = self.make_trip(job)

		defaults = get_purchase_invoice_item_tms_defaults(transport_trip=trip.name)

		self.assertEqual(defaults["tms_transport_trip"], trip.name)
		self.assertEqual(defaults["tms_transport_job"], job.name)
		self.assertEqual(defaults["tms_transport_sales_order"], sales_order.name)
		self.assertEqual(defaults["tms_truck"], self.fixture["vehicle"])
