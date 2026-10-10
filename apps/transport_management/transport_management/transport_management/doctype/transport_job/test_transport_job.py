"""Tests for the standalone Transport Job."""

import unittest

import frappe
from frappe.modules import reload_doc

from transport_management.demo import setup_demo_data
from transport_management.rbac import ROLE_TMS_TRIP_DATA_ENTRY, ROLE_TRANSPORT_MANAGER, ensure_tms_rbac
from transport_management.tms_billing_setup import ensure_tms_billing_setup
from transport_management.transport_management.doctype.transport_job.transport_job import (
	build_transport_sales_invoice,
	calculate_billing_totals,
	calculate_trip_transport_amount,
	evaluate_billing_readiness,
	get_selected_invoice_trips,
	get_billing_review,
	get_billable_trips,
	group_invoice_trips,
	mark_trips_draft_invoiced,
	prepare_billing,
	refresh_quantity_progress,
)
from transport_management.transport_management.doctype.transport_trip.transport_trip import get_defaults_from_transport_job


class TestTransportJob(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		reload_doc("transport_management", "doctype", "transport_job", force=True)

	def setUp(self):
		frappe.db.savepoint("transport_job_test")
		self.demo = setup_demo_data()
		ensure_tms_rbac()
		frappe.db.set_value("Hired Vehicle", self.demo["hired_vehicle"], "vehicle_type", "TIPPER")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="transport_job_test")

	def make_job(self, **values):
		doc = frappe.new_doc("Transport Job")
		doc.update({
			"customer": self.demo["customer"],
			"requested_date": "2026-09-09",
			"loading_site": self.demo["loading_site"],
			"unloading_site": self.demo["offloading_site"],
			"material": self.demo["material"],
			"requested_quantity": 80.8,
			"uom": self.demo["uom"],
		})
		doc.update(values)
		return doc

	def make_trip(self, job, **values):
		doc = frappe.new_doc("Transport Trip")
		doc.update({
			"transport_job": job.name,
			"execution_source": "HIRED",
			"trip_date": job.requested_date,
			"transporter": self.demo["transporter_supplier"],
			"hired_vehicle": self.demo["hired_vehicle"],
			"loading_site": job.loading_site,
			"unloading_site": job.unloading_site,
			"material": job.material,
			"planned_quantity": job.requested_quantity,
			"uom": job.uom,
		})
		doc.update(values)
		return doc

	def advance_trip(self, trip, status, quantity=None):
		if status in {"ASSIGNED", "LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"}:
			trip.status = "ASSIGNED"
			trip.save()
		if status in {"LOADED", "IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"}:
			trip.status = "LOADED"
			trip.loaded_quantity = quantity or trip.planned_quantity
			trip.save()
		if status in {"IN_TRANSIT", "DELIVERED", "POD_RECEIVED", "CLOSED"}:
			trip.status = "IN_TRANSIT"
			trip.save()
		if status in {"DELIVERED", "POD_RECEIVED", "CLOSED"}:
			trip.status = "DELIVERED"
			trip.delivered_quantity = quantity or trip.planned_quantity
			trip.save()
		if status in {"POD_RECEIVED", "CLOSED"}:
			trip.status = "POD_RECEIVED"
			trip.pod_attachment = "/files/test-pod.pdf"
			trip.save()
		if status == "CLOSED":
			trip.status = "CLOSED"
			trip.save()
		return trip

	def make_user_with_role(self, role):
		email = f"{frappe.generate_hash(length=10).lower()}@transport-job-billing.test"
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"enabled": 1,
			"first_name": role,
			"new_password": "TMSBilling#2026",
			"roles": [{"role": role}],
		})
		user.insert(ignore_permissions=True)
		frappe.clear_cache(user=email)
		return email

	def make_location(self, usage, active=1):
		location = frappe.new_doc("Transport Location")
		location.update({
			"location": f"TMS {usage} Job Location {frappe.generate_hash(length=8)}",
			"country": "United Arab Emirates",
			"location_usage": usage,
			"active": active,
		})
		location.insert()
		return location.name

	def get_field(self, fieldname):
		return frappe.get_meta("Transport Job").get_field(fieldname)

	def test_form_uses_expected_top_tabs_with_job_details_first(self):
		meta = frappe.get_meta("Transport Job")
		tabs = [field for field in meta.fields if field.fieldtype == "Tab Break"]
		self.assertEqual(
			[field.label for field in tabs],
			["Job Details", "Business References", "Commercial", "Quantity Progress"],
		)
		self.assertEqual(meta.fields[0].fieldname, "job_details_tab")
		self.assertEqual(meta.fields[0].label, "Job Details")

	def test_job_details_tab_contains_core_operational_fields_only(self):
		field_order = [field.fieldname for field in frappe.get_meta("Transport Job").fields]
		job_detail_fields = field_order[
			field_order.index("job_details_tab") + 1:field_order.index("business_references_tab")
		]
		for fieldname in (
			"customer",
			"requested_date",
			"material",
			"requested_quantity",
			"uom",
			"loading_site",
			"unloading_site",
			"status",
			"special_instructions",
		):
			self.assertIn(fieldname, job_detail_fields)
		for fieldname in ("vehicle", "driver", "truck_count"):
			self.assertNotIn(fieldname, job_detail_fields)

	def test_business_reference_visibility_is_clean(self):
		self.assertFalse(self.get_field("sale_order_reference").hidden)
		self.assertFalse(self.get_field("customer_lpo_number").hidden)
		for fieldname in ("sales_order", "sales_order_item", "do_number", "customer_do", "fnrc"):
			self.assertTrue(self.get_field(fieldname).hidden, fieldname)

	def test_commercial_fields_are_visible_and_read_only(self):
		for fieldname in ("agreed_rate", "ordered_amount"):
			field = self.get_field(fieldname)
			self.assertFalse(field.hidden, fieldname)
			self.assertTrue(field.read_only, fieldname)

	def test_quantity_progress_fields_are_visible_and_read_only(self):
		for fieldname in ("assigned_quantity", "loaded_quantity", "delivered_quantity", "remaining_quantity"):
			field = self.get_field(fieldname)
			self.assertFalse(field.hidden, fieldname)
			self.assertTrue(field.read_only, fieldname)

	def test_billing_status_defaults_to_not_ready_and_is_read_only(self):
		field = self.get_field("billing_status")
		self.assertEqual(field.default, "Not Ready")
		self.assertTrue(field.read_only)
		doc = self.make_job()
		doc.insert()
		self.assertEqual(doc.billing_status, "Not Ready")

	def test_standalone_transport_job_creation(self):
		doc = self.make_job()
		doc.insert()
		self.assertRegex(doc.name, r"^TJOB-\d{4}-\d{5}$")
		self.assertEqual(doc.status, "Draft")
		self.assertFalse(doc.get("vehicle"))
		self.assertFalse(doc.get("driver"))
		self.assertFalse(doc.get("pod"))
		self.assertFalse(doc.get("gdn"))

	def test_new_transport_job_defaults_uom_to_ton(self):
		doc = self.make_job(uom="")
		doc.insert()
		self.assertEqual(doc.uom, "TON")

	def test_transport_job_uom_is_read_only_in_metadata(self):
		field = self.get_field("uom")
		self.assertEqual(field.default, "TON")
		self.assertTrue(field.read_only)

	def test_transport_job_rejects_non_ton_uom(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Transport Job UOM must be TON"):
			self.make_job(uom="Tonne").insert()

	def test_existing_ton_transport_job_remains_valid(self):
		doc = self.make_job(uom="TON")
		doc.insert()
		doc.special_instructions = "Existing TON job still saves."
		doc.save()
		self.assertEqual(doc.uom, "TON")

	def test_obsolete_integration_fields_do_not_exist(self):
		meta = frappe.get_meta("Transport Job")
		obsolete_fields = (
			"so" + "urce",
			"".join(("ha", "der", "_shipment_id")),
			"".join(("ha", "der", "_order_id")),
			"external" + "_id",
			"idempotency" + "_key",
		)
		for fieldname in obsolete_fields:
			self.assertIsNone(meta.get_field(fieldname), fieldname)

	def test_positive_quantity_validation(self):
		for quantity in (0, -1):
			with self.subTest(quantity=quantity):
				with self.assertRaises(frappe.ValidationError):
					self.make_job(requested_quantity=quantity).insert()

	def test_loading_and_unloading_sites_must_differ(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_job(unloading_site=self.demo["loading_site"]).insert()

	def test_inactive_location_rejected(self):
		location = frappe.new_doc("Transport Location")
		location.update({
			"location": "TMS Inactive Job Location " + frappe.generate_hash(length=8),
			"country": "United Arab Emirates",
			"location_usage": "Loading",
			"active": 0,
		})
		location.insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_job(loading_site=location.name).insert()

	def test_loading_site_accepts_loading_and_both_usage(self):
		self.make_job(loading_site=self.make_location("Loading")).insert()
		self.make_job(loading_site=self.make_location("Both")).insert()

	def test_loading_site_rejects_unloading_only_usage(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_job(loading_site=self.make_location("Unloading")).insert()

	def test_unloading_site_accepts_unloading_and_both_usage(self):
		self.make_job(unloading_site=self.make_location("Unloading")).insert()
		self.make_job(unloading_site=self.make_location("Both")).insert()

	def test_unloading_site_rejects_loading_only_usage(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_job(unloading_site=self.make_location("Loading")).insert()

	def test_hidden_legacy_reference_values_are_preserved(self):
		doc = self.make_job(
			sale_order_reference="TSO-2026-00001",
			customer_lpo_number="LPO-KEEP",
			do_number="DO-KEEP",
			customer_do="CUSTOMER-DO-KEEP",
			fnrc="FNRC-KEEP",
			agreed_rate=12,
			ordered_amount=969.6,
		)
		doc.insert()
		reloaded = frappe.get_doc("Transport Job", doc.name)
		self.assertEqual(reloaded.sale_order_reference, "TSO-2026-00001")
		self.assertEqual(reloaded.customer_lpo_number, "LPO-KEEP")
		self.assertEqual(reloaded.do_number, "DO-KEEP")
		self.assertEqual(reloaded.customer_do, "CUSTOMER-DO-KEEP")
		self.assertEqual(reloaded.fnrc, "FNRC-KEEP")
		self.assertEqual(reloaded.agreed_rate, 12)
		self.assertEqual(reloaded.ordered_amount, 969.6)

	def test_execution_fields_do_not_belong_to_transport_job(self):
		meta = frappe.get_meta("Transport Job")
		for fieldname in ("vehicle", "driver", "gdn", "loading_no", "unloading_no", "pod", "fuel", "toll_amount"):
			self.assertIsNone(meta.get_field(fieldname), fieldname)

	def test_active_planned_trip_keeps_billing_not_ready(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		self.make_trip(job, planned_quantity=10).insert()
		job.reload()
		self.assertEqual(job.billing_status, "Not Ready")

	def test_active_assigned_trip_keeps_billing_not_ready(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "ASSIGNED")
		job.reload()
		self.assertEqual(job.billing_status, "Not Ready")

	def test_loaded_trip_keeps_billing_not_ready(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "LOADED", quantity=10)
		job.reload()
		self.assertEqual(job.loaded_quantity, 10)
		self.assertEqual(job.delivered_quantity, 0)
		self.assertEqual(job.billing_status, "Not Ready")

	def test_in_transit_trip_keeps_billing_not_ready(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "IN_TRANSIT", quantity=10)
		job.reload()
		self.assertEqual(job.billing_status, "Not Ready")

	def test_exception_trip_keeps_billing_not_ready(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		trip.status = "ASSIGNED"
		trip.save()
		trip.status = "EXCEPTION"
		trip.save()
		job.reload()
		self.assertEqual(job.billing_status, "Not Ready")

	def test_cancelled_trip_does_not_block_billing_readiness(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		cancelled = self.make_trip(job, planned_quantity=10).insert()
		cancelled.status = "CANCELLED"
		cancelled.save()
		closed = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(closed, "CLOSED", quantity=10)
		job.reload()
		self.assertEqual(job.delivered_quantity, 10)
		self.assertEqual(job.remaining_quantity, 0)
		self.assertEqual(job.billing_status, "Ready for Billing")

	def test_closed_trips_with_remaining_quantity_stay_not_ready(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=5).insert()
		self.advance_trip(trip, "CLOSED", quantity=5)
		job.reload()
		self.assertEqual(job.remaining_quantity, 5)
		self.assertEqual(job.billing_status, "Not Ready")

	def test_closed_trips_with_zero_remaining_quantity_are_ready_for_billing(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		job.reload()
		self.assertEqual(job.remaining_quantity, 0)
		self.assertEqual(job.billing_status, "Ready for Billing")

	def test_assigned_quantity_alone_does_not_trigger_billing_readiness(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "ASSIGNED")
		job.reload()
		self.assertEqual(job.assigned_quantity, 10)
		self.assertEqual(job.delivered_quantity, 0)
		self.assertEqual(job.billing_status, "Not Ready")

	def test_loaded_quantity_alone_does_not_trigger_billing_readiness(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "LOADED", quantity=10)
		job.reload()
		self.assertEqual(job.loaded_quantity, 10)
		self.assertEqual(job.delivered_quantity, 0)
		self.assertEqual(job.billing_status, "Not Ready")

	def test_delivered_quantity_updates_billing_readiness_only_after_trip_closes(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "DELIVERED", quantity=10)
		job.reload()
		self.assertEqual(job.delivered_quantity, 10)
		self.assertEqual(job.remaining_quantity, 0)
		self.assertEqual(job.billing_status, "Not Ready")
		self.advance_trip(trip, "CLOSED", quantity=10)
		job.reload()
		self.assertEqual(job.billing_status, "Ready for Billing")

	def test_fully_delivered_job_rejects_new_trip_defaults(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"This Transport Job is fully delivered. No remaining quantity is available for a new Trip.",
		):
			get_defaults_from_transport_job(job.name)

	def test_fully_delivered_job_rejects_direct_new_trip_insert(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"This Transport Job is fully delivered. No remaining quantity is available for a new Trip.",
		):
			self.make_trip(job, planned_quantity=1).insert()

	def test_prepare_billing_rejects_job_that_is_not_ready(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		with self.assertRaisesRegex(frappe.ValidationError, f"Transport Job {job.name} is not ready for billing."):
			prepare_billing(job.name)

	def test_authorized_billing_role_can_prepare_ready_job(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		manager = self.make_user_with_role(ROLE_TRANSPORT_MANAGER)
		frappe.set_user(manager)
		result = prepare_billing(job.name)
		self.assertEqual(result["transport_job"], job.name)
		self.assertEqual(result["billing_status"], "Ready for Billing")

	def test_trip_data_entry_cannot_prepare_billing(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		trip_user = self.make_user_with_role(ROLE_TMS_TRIP_DATA_ENTRY)
		frappe.set_user(trip_user)
		with self.assertRaises(frappe.PermissionError):
			prepare_billing(job.name)

	def test_billing_review_rejects_job_that_is_not_ready(self):
		job = self.make_job(requested_quantity=10)
		job.insert()
		with self.assertRaisesRegex(frappe.ValidationError, f"Transport Job {job.name} is not ready for billing."):
			get_billing_review(job.name)

	def test_authorized_role_can_load_ready_billing_review(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10, gdn="GDN-READY").insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		manager = self.make_user_with_role(ROLE_TRANSPORT_MANAGER)
		frappe.set_user(manager)
		review = get_billing_review(job.name)
		self.assertEqual(review["summary"]["transport_job"], job.name)
		self.assertEqual(review["summary"]["billing_status"], "Ready for Billing")
		self.assertEqual(len(review["trips"]), 1)

	def test_trip_data_entry_cannot_load_billing_review(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10, gdn="GDN-RBAC").insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		trip_user = self.make_user_with_role(ROLE_TMS_TRIP_DATA_ENTRY)
		frappe.set_user(trip_user)
		with self.assertRaises(frappe.PermissionError):
			get_billing_review(job.name)

	def test_billing_review_includes_only_closed_trips(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		closed = self.make_trip(job, planned_quantity=10, gdn="GDN-CLOSED").insert()
		self.advance_trip(closed, "CLOSED", quantity=10)
		self.assertEqual([trip.name for trip in get_billable_trips(job)], [closed.name])

	def test_cancelled_and_exception_trips_are_excluded_from_billable_helper(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		cancelled = self.make_trip(job, planned_quantity=10).insert()
		cancelled.status = "CANCELLED"
		cancelled.save()
		exception = self.make_trip(job, planned_quantity=10).insert()
		exception.status = "ASSIGNED"
		exception.save()
		exception.status = "EXCEPTION"
		exception.save()
		self.assertEqual(get_billable_trips(job), [])

	def test_billing_review_transport_amount_vat_and_net_calculation(self):
		amounts = calculate_trip_transport_amount(81.04, 25.5)
		self.assertEqual(amounts["taxable_amount"], 2066.52)
		self.assertEqual(amounts["vat_amount"], 103.33)
		self.assertEqual(amounts["net_amount"], 2169.85)

	def test_billing_review_totals_aggregate_selected_rows_and_keep_tolls_separate(self):
		rows = [
			{
				"selected": 1,
				"delivered_quantity": 81.04,
				"taxable_amount": 2066.52,
				"vat_amount": 103.33,
				"net_amount": 2169.85,
				"rak_toll": 300,
				"sharjah_toll": 210.25,
				"fnrc_extra_charge": 42,
			},
			{
				"selected": 0,
				"delivered_quantity": 10,
				"taxable_amount": 255,
				"vat_amount": 12.75,
				"net_amount": 267.75,
				"rak_toll": 50,
				"sharjah_toll": 60,
				"fnrc_extra_charge": 70,
			},
		]
		totals = calculate_billing_totals(rows)
		self.assertEqual(totals["selected_trips"], 1)
		self.assertEqual(totals["delivered_quantity"], 81.04)
		self.assertEqual(totals["taxable_amount"], 2066.52)
		self.assertEqual(totals["vat_percent"], 5)
		self.assertEqual(totals["vat_amount"], 103.33)
		self.assertEqual(totals["net_amount"], 2169.85)
		self.assertEqual(totals["rak_toll"], 300)
		self.assertEqual(totals["sharjah_toll"], 210.25)
		self.assertEqual(totals["fnrc_extra_charge"], 42)

	def test_billing_review_does_not_create_invoice_or_change_billing_status(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10, gdn="GDN-NO-INVOICE").insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		before = frappe.db.count("Sales Invoice") if frappe.db.exists("DocType", "Sales Invoice") else 0
		get_billing_review(job.name)
		after = frappe.db.count("Sales Invoice") if frappe.db.exists("DocType", "Sales Invoice") else 0
		self.assertEqual(after, before)
		job.reload()
		self.assertEqual(job.billing_status, "Ready for Billing")

	def test_invoice_trip_validation_rejects_trip_from_another_job(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		other_job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		other_job.insert()
		trip = self.make_trip(other_job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		with self.assertRaisesRegex(frappe.ValidationError, f"does not belong to Transport Job {job.name}"):
			get_selected_invoice_trips(job, [trip.name])

	def test_invoice_trip_validation_rejects_non_closed_trip(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		with self.assertRaisesRegex(frappe.ValidationError, "must be CLOSED"):
			get_selected_invoice_trips(job, [trip.name])

	def test_invoice_trip_validation_rejects_duplicate_billed_trip(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		frappe.db.set_value(
			"Transport Trip",
			trip.name,
			{"transport_billing_status": "Draft Invoice", "transport_sales_invoice": "SINV-00015"},
		)
		with self.assertRaisesRegex(frappe.ValidationError, "already included in Sales Invoice SINV-00015"):
			get_selected_invoice_trips(job, [trip.name])

	def test_draft_invoice_trip_sets_job_billing_in_progress(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		mark_trips_draft_invoiced([trip.name], "SINV-DRAFT-STATUS")
		refresh_quantity_progress(job.name)
		self.assertEqual(frappe.db.get_value("Transport Job", job.name, "billing_status"), "Billing In Progress")

	def test_readiness_evaluator_does_not_reset_draft_invoice_job(self):
		job = self.make_job(requested_quantity=10, agreed_rate=25.5)
		job.insert()
		trip = self.make_trip(job, planned_quantity=10).insert()
		self.advance_trip(trip, "CLOSED", quantity=10)
		mark_trips_draft_invoiced([trip.name], "SINV-DRAFT-EVAL")
		self.assertEqual(evaluate_billing_readiness(job.name), "Billing In Progress")

	def test_partial_draft_billing_keeps_job_in_progress(self):
		job = self.make_job(requested_quantity=30, agreed_rate=25.5)
		job.insert()
		draft_trip = self.make_trip(job, planned_quantity=10).insert()
		open_trip = self.make_trip(job, planned_quantity=20).insert()
		self.advance_trip(draft_trip, "CLOSED", quantity=10)
		self.advance_trip(open_trip, "CLOSED", quantity=20)
		mark_trips_draft_invoiced([draft_trip.name], "SINV-DRAFT-PARTIAL")
		refresh_quantity_progress(job.name)
		self.assertEqual(frappe.db.get_value("Transport Job", job.name, "billing_status"), "Billing In Progress")
		self.assertEqual([trip.name for trip in get_billable_trips(job)], [open_trip.name])

	def test_all_draft_billed_trips_keep_job_in_progress_and_review_excludes_them(self):
		job = self.make_job(requested_quantity=30, agreed_rate=25.5)
		job.insert()
		first = self.make_trip(job, planned_quantity=10).insert()
		second = self.make_trip(job, planned_quantity=20).insert()
		self.advance_trip(first, "CLOSED", quantity=10)
		self.advance_trip(second, "CLOSED", quantity=20)
		mark_trips_draft_invoiced([first.name, second.name], "SINV-DRAFT-ALL")
		refresh_quantity_progress(job.name)
		manager = self.make_user_with_role(ROLE_TRANSPORT_MANAGER)
		frappe.set_user(manager)
		review = get_billing_review(job.name)
		self.assertEqual(review["summary"]["billing_status"], "Billing In Progress")
		self.assertEqual(review["trips"], [])
		self.assertEqual(review["summary"]["existing_invoices"][0]["invoice"], "SINV-DRAFT-ALL")
		self.assertEqual(review["summary"]["existing_invoices"][0]["trips"], 2)

	def test_invoice_grouping_aggregates_by_route_material_and_rate(self):
		job = self.make_job(requested_quantity=30, agreed_rate=20)
		job.insert()
		first = self.make_trip(job, planned_quantity=10).insert()
		second = self.make_trip(job, planned_quantity=20).insert()
		self.advance_trip(first, "CLOSED", quantity=10)
		self.advance_trip(second, "CLOSED", quantity=20)
		trips = get_selected_invoice_trips(job, [first.name, second.name])
		groups = group_invoice_trips(job, trips)
		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0]["qty"], 30)
		self.assertEqual(groups[0]["rate"], 20)

	def test_invoice_grouping_separates_same_material_different_loading_site(self):
		job = self.make_job(requested_quantity=30, agreed_rate=20)
		job.insert()
		first = frappe._dict({
			"material": job.material,
			"loading_site": "MASAFI CRUSHER",
			"unloading_site": "AJMAN TECH REMIX",
			"delivered_quantity": 10,
		})
		second = frappe._dict({
			"material": job.material,
			"loading_site": "NATIONAL QUARRIES",
			"unloading_site": "AJMAN TECH REMIX",
			"delivered_quantity": 20,
		})
		self.assertEqual(len(group_invoice_trips(job, [first, second])), 2)

	def test_invoice_grouping_separates_same_material_different_unloading_site(self):
		job = self.make_job(requested_quantity=30, agreed_rate=20)
		job.insert()
		first = frappe._dict({
			"material": job.material,
			"loading_site": "MASAFI CRUSHER",
			"unloading_site": "AJMAN TECH REMIX",
			"delivered_quantity": 10,
		})
		second = frappe._dict({
			"material": job.material,
			"loading_site": "MASAFI CRUSHER",
			"unloading_site": "DUBAI TECH REMIX",
			"delivered_quantity": 20,
		})
		self.assertEqual(len(group_invoice_trips(job, [first, second])), 2)

	def test_invoice_grouping_separates_same_route_material_different_rate(self):
		job = self.make_job(requested_quantity=30, agreed_rate=20)
		job.insert()
		first = frappe._dict({
			"material": job.material,
			"loading_site": "MASAFI CRUSHER",
			"unloading_site": "AJMAN TECH REMIX",
			"delivered_quantity": 10,
			"unit_rate": 20,
		})
		second = frappe._dict({
			"material": job.material,
			"loading_site": "MASAFI CRUSHER",
			"unloading_site": "AJMAN TECH REMIX",
			"delivered_quantity": 20,
			"unit_rate": 25.5,
		})
		self.assertEqual(len(group_invoice_trips(job, [first, second])), 2)

	def test_transport_invoice_rows_store_route_material_fields(self):
		ensure_tms_billing_setup()
		job = self.make_job(requested_quantity=30, agreed_rate=20)
		job.insert()
		groups = [
			{
				"material": job.material,
				"loading_site": job.loading_site,
				"unloading_site": job.unloading_site,
				"rate": 20,
				"qty": 30,
				"trip_names": ["TRIP-1"],
			}
		]
		invoice = build_transport_sales_invoice(
			job=job,
			company=frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", pluck="name", limit=1)[0],
			service_item="Transport Service",
			tax_template=None,
			income_account="Sales - T",
			cost_center=None,
			groups=groups,
		)
		row = invoice.items[0]
		self.assertEqual(row.tms_loading_location, job.loading_site)
		self.assertEqual(row.tms_unloading_location, job.unloading_site)
		self.assertEqual(row.tms_material, job.material)
		self.assertEqual(row.tms_transport_job, job.name)
		self.assertEqual(row.tms_route_description, f"{job.loading_site} - {job.unloading_site} - {job.material}")

	def test_transport_invoice_tracking_marks_selected_trips_only(self):
		job = self.make_job(requested_quantity=30, agreed_rate=20)
		job.insert()
		selected = self.make_trip(job, planned_quantity=10).insert()
		unselected = self.make_trip(job, planned_quantity=20).insert()
		self.advance_trip(selected, "CLOSED", quantity=10)
		self.advance_trip(unselected, "CLOSED", quantity=20)
		mark_trips_draft_invoiced([selected.name], "SINV-TRACK")
		self.assertEqual(frappe.db.get_value("Transport Trip", selected.name, "transport_billing_status"), "Draft Invoice")
		self.assertEqual(frappe.db.get_value("Transport Trip", selected.name, "transport_sales_invoice"), "SINV-TRACK")
		self.assertEqual(
			frappe.db.get_value("Transport Trip", unselected.name, "transport_billing_status"),
			"Not Billed",
		)
		self.assertFalse(frappe.db.get_value("Transport Trip", unselected.name, "transport_sales_invoice"))
