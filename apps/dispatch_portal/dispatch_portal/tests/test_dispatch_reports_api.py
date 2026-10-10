"""Reports API tests."""

import frappe
from frappe.utils import add_days, today

from dispatch_portal.tests.test_helpers import DispatchTestCase, make_user


class TestDispatchReportsApi(DispatchTestCase):
	def setUp(self):
		super().setUp()
		self.manager = make_user(["Transport Manager"], "Reports Manager")
		self.outsider = make_user(["Website Manager"], "Reports Outsider")

	def test_reports_overview_shape(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.reports import get_reports

		data = get_reports()
		for key in (
			"range",
			"trips_by_status",
			"trips_by_execution_source",
			"trips_by_customer",
			"quantity_delivered",
			"document_verification",
			"fleet_utilization",
			"daily_trip_volume",
		):
			self.assertIn(key, data)

		statuses = {row["key"]: row["count"] for row in data["trips_by_status"]}
		self.assertGreaterEqual(statuses.get("PLANNED", 0), 1)
		self.assertEqual(data["quantity_delivered"]["planned"], 40)
		self.assertTrue(all("date" in row for row in data["daily_trip_volume"]))

	def test_reports_customer_rollup_uses_the_transport_job(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.reports import get_reports

		data = get_reports()
		customers = {row["key"]: row["count"] for row in data["trips_by_customer"]}
		self.assertIn(self.customer, customers)

	def test_reports_driver_rollup(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.reports import get_driver_report

		data = get_driver_report()
		drivers = {row["driver"]: row for row in data["rows"]}
		self.assertIn(self.driver, drivers)
		self.assertGreaterEqual(drivers[self.driver]["trips"], 1)

	def test_trip_report_rows(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.reports import get_trip_report

		data = get_trip_report()
		self.assertIn(self.trip, [row["trip"] for row in data["rows"]])

	def test_pod_backlog(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Transport Trip", self.trip, "status", "DELIVERED")
		frappe.set_user(self.manager)
		from dispatch_portal.api.reports import get_pod_backlog

		data = get_pod_backlog()
		self.assertIn(self.trip, [row["trip"] for row in data["rows"]])

	def test_reports_respect_the_requested_range(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.reports import get_reports

		data = get_reports(
			from_date=add_days(today(), -10), to_date=add_days(today(), -8)
		)
		self.assertEqual(data["trips_by_status"], [])
		self.assertEqual(data["quantity_delivered"]["planned"], 0)

	def test_reports_deny_outsider(self):
		frappe.set_user(self.outsider)
		from dispatch_portal.api.reports import get_reports

		self.assertRaises(frappe.PermissionError, get_reports)
