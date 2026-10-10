"""Trips API tests: listing, assignment and delegated status transitions."""

import frappe

from dispatch_portal.tests.test_helpers import DispatchTestCase, make_user


class TestDispatchTripsApi(DispatchTestCase):
	def setUp(self):
		super().setUp()
		self.manager = make_user(["Transport Manager"], "Trips Manager")
		self.entry_user = make_user(["TMS Trip Data Entry"], "Trips Entry")
		self.outsider = make_user(["Website Manager"], "Trips Outsider")

	def test_trips_list_returns_the_test_trip(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.trips import get_trips

		data = get_trips(filters={"search": self.trip})
		rows = {row["trip"]: row for row in data["trips"]}
		self.assertIn(self.trip, rows)
		row = rows[self.trip]
		self.assertEqual(row["status"], "PLANNED")
		self.assertEqual(row["customer"], self.customer)
		self.assertEqual(row["route"], f"{self.loading_site} -> {self.unloading_site}")

	def test_trips_filters_by_status(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.trips import get_trips

		data = get_trips(filters={"status": "IN_TRANSIT"})
		self.assertTrue(all(row["status"] == "IN_TRANSIT" for row in data["trips"]))

	def test_trips_filters_by_date_range(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.trips import get_trips

		from frappe.utils import add_days, today

		data = get_trips(
			filters={
				"from_date": add_days(today(), -1),
				"to_date": add_days(today(), 1),
			}
		)
		names = [row["trip"] for row in data["trips"]]
		self.assertIn(self.trip, names)

	def test_trips_count_matches_the_filter(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.trips import get_trip_count

		result = get_trip_count(filters={"search": self.trip})
		self.assertGreaterEqual(result["count"], 1)

	def test_trip_detail_reads_real_tms_relationships(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.trips import get_trip

		data = get_trip(self.trip)
		self.assertEqual(data["transport_job"], self.job)
		self.assertEqual(data["job"]["customer"], self.customer)
		self.assertEqual(data["job"]["requested_quantity"], 100)
		self.assertEqual(data["vehicle"], self.truck)
		self.assertEqual(data["driver"], self.driver)
		self.assertEqual(data["uom"], "TON")

	def test_trips_api_denies_outsider(self):
		frappe.set_user(self.outsider)
		from dispatch_portal.api.trips import get_trip, get_trips

		self.assertRaises(frappe.PermissionError, get_trips)
		self.assertRaises(frappe.PermissionError, get_trip, self.trip)

	def test_transition_uses_the_tms_whitelisted_service(self):
		"""The console must not reimplement the status workflow."""
		frappe.set_user(self.manager)
		from dispatch_portal.api.trips import transition_trip

		result = transition_trip(self.trip, "ASSIGNED")
		self.assertEqual(result["status"], "ASSIGNED")
		self.assertEqual(
			frappe.db.get_value("Transport Trip", self.trip, "status"), "ASSIGNED"
		)

	def test_transition_rejects_invalid_status(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.trips import transition_trip

		self.assertRaises(frappe.ValidationError, transition_trip, self.trip, "NOT_A_STATUS")

	def test_transition_is_denied_for_outsider(self):
		frappe.set_user(self.outsider)
		from dispatch_portal.api.trips import transition_trip

		self.assertRaises(frappe.PermissionError, transition_trip, self.trip, "ASSIGNED")

	def test_assign_trip_sets_vehicle_driver_and_status(self):
		from dispatch_portal.tests.test_helpers import make_driver, make_job, make_trip, make_truck

		truck = make_truck("101")
		driver = make_driver("201")
		job = self.make_job()
		trip = make_trip(
			job,
			self.loading_site,
			self.unloading_site,
			vehicle=truck,
			driver=driver,
			status="PLANNED",
		)

		frappe.set_user(self.manager)
		from dispatch_portal.api.trips import assign_trip

		result = assign_trip(trip, vehicle=truck, driver=driver)
		self.assertEqual(result["trip"]["vehicle"], truck)
		self.assertEqual(result["trip"]["driver"], driver)
		self.assertEqual(result["trip"]["status"], "ASSIGNED")

	def test_assign_trip_rejects_unknown_truck(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.trips import assign_trip

		self.assertRaises(
			frappe.ValidationError, assign_trip, self.trip, vehicle="NO-SUCH-TRUCK"
		)

	def test_assign_trip_rejects_terminal_trip(self):
		from dispatch_portal.api.trips import assign_trip

		frappe.set_user("Administrator")
		frappe.db.set_value("Transport Trip", self.trip, "status", "CLOSED")
		frappe.set_user(self.manager)
		self.assertRaises(frappe.ValidationError, assign_trip, self.trip, vehicle=self.truck)

	def test_assignment_options_report_reserved_trucks(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.trips import get_assignment_options

		data = get_assignment_options()
		reserved = {row["name"] for row in data["trucks"] if row["reserved"]}
		self.assertIn(self.truck, reserved)
		self.assertTrue(all(row["status"] == "Active" for row in data["drivers"]))

	def test_status_flow_metadata(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.trips import get_status_flow

		statuses = {row["value"] for row in get_status_flow()["statuses"]}
		for status in ("PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "CLOSED"):
			self.assertIn(status, statuses)

	def make_job(self):
		from dispatch_portal.tests.test_helpers import make_job

		return make_job(self.customer, self.loading_site, self.unloading_site, quantity=50)
