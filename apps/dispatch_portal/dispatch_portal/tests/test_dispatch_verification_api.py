"""Verification API tests.

These lock in requirement "never allow AI extraction to automatically overwrite
authoritative trip data": the extraction payload is advisory, only allow-listed
documentation fields can be written, only on an explicit verifier action, and
rejection never writes anything.
"""

import frappe

from dispatch_portal.tests.test_helpers import DispatchTestCase, make_user

WRITABLE_BY_EXTRACTION = (
	"gdn",
	"pod_received_at",
	"rak_toll",
	"sharjah_toll",
	"fnrc_extra_charge",
)

NEVER_WRITABLE = (
	"status",
	"planned_quantity",
	"loaded_quantity",
	"delivered_quantity",
	"actual_quantity",
	"vehicle",
	"driver",
	"material",
	"loading_site",
	"unloading_site",
	"transport_job",
	"rak_toll",  # asserted per document type below
)


class TestDispatchVerificationApi(DispatchTestCase):
	def setUp(self):
		super().setUp()
		self.manager = make_user(["Transport Manager"], "Verify Manager")
		self.dispatcher_only = make_user(["AL RANA Dispatcher"], "Verify Dispatcher")
		self.outsider = make_user(["Website Manager"], "Verify Outsider")
		from dispatch_portal.tests.test_helpers import make_trip_document

		self.document = make_trip_document(self.trip, self.driver)

	# ------------------------------------------------------------------ queue

	def test_review_queue_lists_the_document(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import get_verification_queue

		data = get_verification_queue()
		names = [row["name"] for row in data["documents"]]
		self.assertIn(self.document, names)
		row = next(item for item in data["documents"] if item["name"] == self.document)
		self.assertEqual(row["verification_status"], "PENDING_REVIEW")
		self.assertEqual(row["ai_status"], "PROCESSED")
		self.assertEqual(row["document_type_label"], "Aber Toll")
		self.assertGreaterEqual(data["total"], 1)

	def test_review_queue_denies_non_verifier(self):
		frappe.set_user(self.dispatcher_only)
		from dispatch_portal.api.verification import get_verification_queue

		self.assertRaises(frappe.PermissionError, get_verification_queue)

	def test_review_summary_counts_backlog(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import get_verification_summary

		summary = get_verification_summary()
		self.assertGreaterEqual(summary["pending_review"], 1)
		self.assertEqual(summary["by_document_type"].get("ABER_TOLL", 0), 1)

	# ----------------------------------------------------------------- detail

	def test_document_review_exposes_candidates(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import get_verification_document

		data = get_verification_document(self.document)
		candidates = {row["extracted_field"]: row for row in data["candidates"]}

		self.assertIn("extracted_amount", candidates)
		self.assertIn("extracted_ticket_number", candidates)
		self.assertIn("extracted_receipt_number", candidates)

		# The receipt number is reference only and can never touch the trip.
		self.assertFalse(candidates["extracted_receipt_number"]["can_write_trip"])
		self.assertIsNone(candidates["extracted_receipt_number"]["trip_field"])

		# Charge amounts map to the matching toll field of the trip.
		self.assertEqual(candidates["extracted_amount"]["trip_field"], "rak_toll")
		self.assertTrue(candidates["extracted_amount"]["can_write_trip"])

		# The business fields the AI also "saw" are never writable.
		for field in ("extracted_customer", "extracted_net_weight"):
			self.assertIn(field, candidates)
			self.assertFalse(candidates[field]["can_write_trip"])

		trip_context = data["trip"]
		self.assertEqual(trip_context["trip"], self.trip)
		self.assertEqual(trip_context["status"], "PLANNED")

	def test_no_candidate_ever_maps_to_a_business_field(self):
		frappe.set_user("Administrator")
		from dispatch_portal.services.verification_service import EXTRACTION_CANDIDATES

		targets = {
			trip_field
			for trip_field, _ in EXTRACTION_CANDIDATES.values()
			if trip_field and trip_field != "__charge_amount__"
		}
		self.assertTrue(targets.issubset(set(WRITABLE_BY_EXTRACTION)))
		for forbidden in NEVER_WRITABLE:
			if forbidden in WRITABLE_BY_EXTRACTION:
				continue
			self.assertNotIn(forbidden, targets)

	def test_extraction_never_writes_without_an_explicit_accept(self):
		"""Loading a document for review must not change the trip at all."""
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import (
			get_verification_document,
			get_verification_queue,
			get_verification_summary,
		)

		get_verification_queue()
		get_verification_document(self.document)
		get_verification_summary()

		trip = self.reload("Transport Trip", self.trip)
		self.assertEqual(trip.rak_toll, 0)
		self.assertIsNone(trip.gdn)
		self.assertEqual(trip.planned_quantity, 40)
		self.assertEqual(trip.status, "PLANNED")
		self.assertEqual(trip.vehicle, self.truck)
		self.assertEqual(trip.driver, self.driver)
		self.assertEqual(trip.transport_job, self.job)

	# ------------------------------------------------------------------ apply

	def test_apply_writes_only_accepted_fields(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import apply_extraction_values

		result = apply_extraction_values(self.document, [{"extracted_field": "extracted_amount"}])
		self.assertEqual(result["applied_fields"], ["extracted_amount"])
		self.assertEqual(result["trip_updates"], {"rak_toll": 123.45})

		trip = self.reload("Transport Trip", self.trip)
		self.assertEqual(trip.rak_toll, 123.45)

		document = self.reload("Transport Trip Document", self.document)
		self.assertEqual(document.verification_status, "APPROVED")
		self.assertEqual(document.verified_by, self.manager)
		self.assertTrue(document.verified_at)

	def test_apply_writes_the_reference_fields_the_verifier_selected(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import apply_extraction_values

		apply_extraction_values(
			self.document,
			[{"extracted_field": "extracted_ticket_number"}],
		)
		trip = self.reload("Transport Trip", self.trip)
		self.assertEqual(trip.gdn, "AI-GDN-0001")
		self.assertEqual(trip.rak_toll, 0)

	def test_apply_rejects_unauthorised_trip_fields(self):
		"""Business fields are silently ignored, so an approval can never touch them."""
		from dispatch_portal.tests.test_helpers import make_trip_document

		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import apply_extraction_values

		for index, forbidden in enumerate(
			("status", "delivered_quantity", "driver", "vehicle", "transport_job", "planned_quantity")
		):
			document = make_trip_document(
				self.trip,
				self.driver,
				file_url=f"/files/dispatch-test-forbidden-{index}.pdf",
			)
			self.assertRaises(
				frappe.ValidationError,
				apply_extraction_values,
				document,
				[{"extracted_field": forbidden}],
			)
			self.assertEqual(
				self.reload("Transport Trip Document", document).verification_status,
				"PENDING_REVIEW",
				"A rejected apply must not approve the document",
			)

		trip = self.reload("Transport Trip", self.trip)
		self.assertEqual(trip.planned_quantity, 40)
		self.assertEqual(trip.status, "PLANNED")
		self.assertEqual(trip.vehicle, self.truck)
		self.assertEqual(trip.driver, self.driver)
		self.assertEqual(trip.transport_job, self.job)

	def test_apply_ignores_unauthorised_fields_mixed_with_valid_ones(self):
		"""A partially valid selection only applies the allow-listed part."""
		from dispatch_portal.tests.test_helpers import make_trip_document

		document = make_trip_document(
			self.trip, self.driver, file_url="/files/dispatch-test-mixed.pdf"
		)
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import apply_extraction_values

		result = apply_extraction_values(
			document,
			[
				{"extracted_field": "delivered_quantity"},
				{"extracted_field": "extracted_amount"},
			],
		)
		self.assertEqual(result["applied_fields"], ["extracted_amount"])

		trip = self.reload("Transport Trip", self.trip)
		self.assertEqual(trip.rak_toll, 123.45)
		self.assertEqual(trip.planned_quantity, 40)

	def test_apply_without_a_selection_is_rejected(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import apply_extraction_values

		self.assertRaises(frappe.ValidationError, apply_extraction_values, self.document, [])
		self.assertEqual(
			self.reload("Transport Trip", self.trip).rak_toll,
			0,
		)

	def test_apply_requires_a_verifier_role(self):
		frappe.set_user(self.dispatcher_only)
		from dispatch_portal.api.verification import apply_extraction_values

		self.assertRaises(
			frappe.PermissionError,
			apply_extraction_values,
			self.document,
			[{"extracted_field": "extracted_amount"}],
		)

	def test_apply_requires_document_write_permission_on_the_trip(self):
		"""Approving writes authoritative trip data, so write access is enforced."""
		verifier_only = make_user(["AL RANA Dispatch Verifier"], "Portal Verifier")
		frappe.set_user(verifier_only)
		from dispatch_portal.api.verification import apply_extraction_values

		self.assertRaises(
			frappe.PermissionError,
			apply_extraction_values,
			self.document,
			[{"extracted_field": "extracted_amount"}],
		)

		# Nothing was written to the trip and the document is still pending.
		self.assertEqual(self.reload("Transport Trip", self.trip).rak_toll, 0)
		self.assertEqual(
			self.reload("Transport Trip Document", self.document).verification_status,
			"PENDING_REVIEW",
		)

	def test_document_cannot_be_verified_twice(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import apply_extraction_values

		apply_extraction_values(self.document, [{"extracted_field": "extracted_amount"}])
		self.assertRaises(
			frappe.ValidationError,
			apply_extraction_values,
			self.document,
			[{"extracted_field": "extracted_amount"}],
		)

	# ----------------------------------------------------------------- reject

	def test_rejection_never_writes_trip_data(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import reject_document_review

		result = reject_document_review(self.document, "Numbers do not match the receipt")
		self.assertEqual(result["document"]["verification_status"], "REJECTED")

		trip = self.reload("Transport Trip", self.trip)
		self.assertEqual(trip.rak_toll, 0)
		self.assertIsNone(trip.gdn)
		self.assertEqual(trip.planned_quantity, 40)

		document = self.reload("Transport Trip Document", self.document)
		self.assertEqual(document.review_notes, "Numbers do not match the receipt")
		self.assertEqual(document.verified_by, self.manager)

	def test_rejection_requires_a_note(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import reject_document_review

		reject_document_review(self.document, None)
		document = self.reload("Transport Trip Document", self.document)
		self.assertTrue(document.review_notes)

	def test_rejection_denies_non_verifier(self):
		frappe.set_user(self.dispatcher_only)
		from dispatch_portal.api.verification import reject_document_review

		self.assertRaises(frappe.PermissionError, reject_document_review, self.document, "no")

	# ------------------------------------------------------------------ reset

	def test_reset_returns_the_document_to_the_queue(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import reject_document_review, reset_document_review

		reject_document_review(self.document, "wrong document")
		reset_document_review(self.document)

		document = self.reload("Transport Trip Document", self.document)
		self.assertEqual(document.verification_status, "PENDING_REVIEW")
		self.assertIsNone(document.verified_by)

	# ------------------------------------------------------------- allowlist

	def test_charge_amount_maps_to_the_matching_trip_field(self):
		from dispatch_portal.tests.test_helpers import make_trip_document

		for document_type, expected_field in (
			("ABER_TOLL", "rak_toll"),
			("SHARJAH_TOLL", "sharjah_toll"),
			("FNRC_RECEIPT", "fnrc_extra_charge"),
		):
			doc_name = make_trip_document(
				self.trip, self.driver, document_type=document_type,
				file_url=f"/files/dispatch-test-{document_type}.pdf",
			)
			if document_type == "LOADING_PAPER":
				continue
			frappe.set_user(self.manager)
			from dispatch_portal.api.verification import get_verification_document

			candidates = {
				row["extracted_field"]: row
				for row in get_verification_document(doc_name)["candidates"]
			}
			self.assertEqual(candidates["extracted_amount"]["trip_field"], expected_field)

	def test_pod_datetime_is_only_writable_for_pod_documents(self):
		from dispatch_portal.tests.test_helpers import make_trip_document

		toll = make_trip_document(
			self.trip, self.driver, "SHARJAH_TOLL", "/files/dispatch-test-sharjah.pdf"
		)
		loading = make_trip_document(
			self.trip, self.driver, "LOADING_PAPER", "/files/dispatch-test-loading.pdf"
		)

		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import get_verification_document

		toll_candidates = {
			row["extracted_field"]: row
			for row in get_verification_document(toll)["candidates"]
		}
		self.assertNotIn("extracted_document_datetime", toll_candidates)

		loading_candidates = {
			row["extracted_field"]: row
			for row in get_verification_document(loading)["candidates"]
		}
		self.assertTrue(
			loading_candidates["extracted_document_datetime"]["can_write_trip"]
		)
		self.assertEqual(
			loading_candidates["extracted_document_datetime"]["trip_field"], "pod_received_at"
		)

	def test_document_types_are_exposed_for_the_console_filter(self):
		frappe.set_user(self.manager)
		from dispatch_portal.api.verification import get_document_types

		values = {row["value"] for row in get_document_types()}
		self.assertIn("ABER_TOLL", values)
		self.assertIn("LOADING_PAPER", values)
		self.assertIn("OFFLOADING_PAPER", values)
