"""Dashboard and map API tests using real TMS data."""

import frappe

from dispatch_portal.tests.test_helpers import DispatchTestCase, make_user


class TestDispatchDashboardApi(DispatchTestCase):
	def setUp(self):
		super().setUp()
		self.manager = make_user(["Transport Manager"], "Dashboard Manager")
		self.entry_user = make_user(["TMS Trip Data Entry"], "Dashboard Entry")
		self.outsider = make_user(["Website Manager"], "Dashboard Outsider")

	def test_dashboard_returns_expected_shape(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.dashboard import get_dashboard

		data = get_dashboard()
		for key in ("kpis", "status_breakdown", "active_trips", "attention_trips", "pending_pod", "verification"):
			self.assertIn(key, data)

		kpis = data["kpis"]
		for key in (
			"trips_today",
			"planned",
			"in_transit",
			"pod_pending",
			"exception",
			"active_jobs",
			"available_trucks",
			"active_drivers",
		):
			self.assertIn(key, kpis)
			self.assertIsInstance(kpis[key], int)

		breakdown = {row["status"]: row["count"] for row in data["status_breakdown"]}
		self.assertGreaterEqual(breakdown.get("PLANNED", 0), 1)

	def test_dashboard_active_trips_use_real_trip_data(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.dashboard import get_dashboard

		data = get_dashboard()
		trip_names = [row["trip"] for row in data["active_trips"]]
		self.assertIn(self.trip, trip_names)

		trip_row = next(row for row in data["active_trips"] if row["trip"] == self.trip)
		self.assertEqual(trip_row["route"], f"{self.loading_site} -> {self.unloading_site}")
		self.assertEqual(trip_row["vehicle"], self.truck)
		self.assertEqual(trip_row["driver"], self.driver)
		self.assertEqual(trip_row["customer"], self.customer)

	def test_dashboard_denies_user_without_console_access(self):
		frappe.set_user(self.outsider)
		from dispatch_portal.api.dashboard import get_dashboard

		self.assertRaises(frappe.PermissionError, get_dashboard)

	def test_dashboard_verification_backlog_for_verifier(self):
		document = self.make_document()
		frappe.set_user(self.manager)
		from dispatch_portal.api.dashboard import get_dashboard

		data = get_dashboard()
		self.assertGreaterEqual(data["verification"]["pending_review"], 1)
		self.assertEqual(data["verification"]["approved"], 0)

	def test_dashboard_verification_backlog_hidden_for_non_verifier(self):
		frappe.set_user(self.entry_user)
		from dispatch_portal.api.dashboard import get_dashboard

		data = get_dashboard()
		self.assertEqual(data["verification"]["pending_review"], 0)

	def make_document(self):
		from dispatch_portal.tests.test_helpers import make_trip_document

		return make_trip_document(self.trip, self.driver)


class TestDispatchTripMapApi(DispatchTestCase):
	def test_map_returns_geolocated_trips(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.trip_map import get_map_data

		data = get_map_data()
		self.assertGreaterEqual(data["total_trips"], 1)
		self.assertGreaterEqual(data["located_trips"], 1)
		self.assertEqual(data["unlocated_trips"], data["total_trips"] - data["located_trips"])

		markers = {row["trip"]: row for row in data["markers"]}
		self.assertIn(self.trip, markers)
		marker = markers[self.trip]
		self.assertAlmostEqual(marker["origin"]["latitude"], 25.2048, places=4)
		self.assertAlmostEqual(marker["destination"]["longitude"], 55.2261, places=4)
		self.assertTrue(marker["origin"]["geolocated"])
		self.assertEqual(marker["status"], "PLANNED")
		self.assertEqual(marker["vehicle"], self.truck)

	def test_map_respects_the_status_group_filter(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.trip_map import get_map_data

		planned = get_map_data(filters={"status_group": "planned"})
		self.assertTrue(all(row["status"] == "PLANNED" for row in planned["markers"]))

		closed = get_map_data(filters={"status_group": "cancelled"})
		self.assertNotIn(self.trip, [row["trip"] for row in closed["markers"]])

	def test_map_ignores_unknown_status_group(self):
		frappe.set_user("Administrator")
		from dispatch_portal.api.trip_map import get_map_data

		data = get_map_data(filters={"status_group": "not-a-group"})
		self.assertGreaterEqual(data["total_trips"], 1)

	def test_map_denies_user_without_console_access(self):
		frappe.set_user(make_user(["Website Manager"], "Map Outsider"))
		from dispatch_portal.api.trip_map import get_map_data

		self.assertRaises(frappe.PermissionError, get_map_data)
