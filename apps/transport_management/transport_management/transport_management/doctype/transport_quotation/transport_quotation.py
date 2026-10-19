# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

APPROVAL_ROLES = {"Transport Manager", "Transport Admin", "System Manager"}
APPROVAL_IMMUTABLE_FIELDS = (
	"quotation_date",
	"customer",
	"valid_until",
	"currency",
	"customer_reference",
	"service_period_from",
	"service_period_to",
	"revision_of",
	"revision_reason",
	"materials",
	"locations",
	"rates",
	"estimated_quantity",
	"estimated_trips",
	"customer_approval_date",
	"customer_approval_reference",
	"customer_approval_notes",
	"customer_approval_attachment",
	"remarks",
)


class TransportQuotation(Document):
	def _validate_selects(self):
		# Ensure runtime Select validation allows Pending Approval and Rejected even before
		# bench migrate synchronizes the updated DocField options in tabDocField.
		status_df = self.meta.get_field("status")
		if status_df and status_df.options:
			opts = status_df.options.split("\n")
			for extra in ("Pending Approval", "Rejected"):
				if extra not in opts:
					opts.append(extra)
			status_df.options = "\n".join(opts)
		super()._validate_selects()

	def before_validate(self):
		if not self.quotation_date:
			self.quotation_date = today()
		if not self.currency:
			self.currency = "AED"

		if self.docstatus == 1:
			self.status = "Approved"
		elif self.docstatus == 2:
			self.status = "Cancelled"
		else:
			if self.is_new():
				if self.status not in {"Draft", "Pending Approval"}:
					self.status = "Draft"
			else:
				previous = self.get_doc_before_save()
				prev_status = previous.status if previous else "Draft"
				if prev_status == "Rejected" and not getattr(self.flags, "in_lifecycle_transition", False):
					self.status = "Rejected"
				elif getattr(self.flags, "in_lifecycle_transition", False) and self.status in {
					"Draft",
					"Pending Approval",
					"Rejected",
				}:
					pass
				elif self.status in {"Draft", "Pending Approval"}:
					pass
				else:
					self.status = prev_status if prev_status in {"Draft", "Pending Approval", "Rejected"} else "Draft"

	def validate(self):
		self.validate_currency()
		self.validate_dates()
		self.validate_revision()
		self.validate_materials_and_locations()
		self.validate_rates(require_complete=self.is_submit_action() or self.is_send_to_customer_action())
		self.validate_approved_immutability()
		self.validate_rejected_immutability()

	def before_submit(self):
		check_lifecycle_authorization(_("record customer approval"))
		previous = self.get_doc_before_save()
		if (previous and previous.status == "Rejected") or self.status == "Rejected":
			frappe.throw(_("Rejected quotations cannot be approved. Create a new quotation or revision instead."))
		self.validate_approval_record()
		self.status = "Approved"

	def on_submit(self):
		ref_text = f" (Ref: {self.customer_approval_reference})" if self.customer_approval_reference else ""
		self.add_comment(
			"Info",
			_("Customer approval recorded on {0}{1} by {2}.").format(
				self.customer_approval_date, ref_text, frappe.session.user
			),
		)

	def on_cancel(self):
		check_lifecycle_authorization(_("cancel an approved quotation"))
		self.status = "Cancelled"
		frappe.db.set_value(self.doctype, self.name, "status", "Cancelled", update_modified=False)
		self.add_comment(
			"Info",
			_("Quotation cancelled by {0}.").format(frappe.session.user),
		)

	def is_submit_action(self):
		return getattr(self, "_action", None) == "submit" or self.docstatus == 1

	def is_send_to_customer_action(self):
		return bool(getattr(self.flags, "in_send_to_customer", False)) or self.status == "Pending Approval"

	def validate_currency(self):
		if self.currency != "AED":
			frappe.throw(_("Transport Quotations use AED for V1."))
		self.currency = "AED"

	def validate_dates(self):
		if self.quotation_date and self.valid_until and getdate(self.valid_until) < getdate(self.quotation_date):
			frappe.throw(_("Acceptance Valid Until cannot be before the Quotation Date."))

		service_from = self.service_period_from
		service_to = self.service_period_to
		if bool(service_from) != bool(service_to):
			frappe.throw(_("Enter both Service Period From and Service Period To, or leave both blank."))
		if service_from and getdate(service_to) < getdate(service_from):
			frappe.throw(_("Service Period To cannot be before Service Period From."))

		for fieldname, label in (
			("estimated_quantity", _("Estimated Quantity")),
			("estimated_trips", _("Estimated Trips")),
		):
			value = self.get(fieldname)
			if value in (None, ""):
				continue
			try:
				estimate = float(value)
			except (TypeError, ValueError):
				frappe.throw(_("{0} must be a number.").format(label))
			if not isfinite(estimate) or estimate < 0:
				frappe.throw(_("{0} cannot be negative or non-finite.").format(label))

	def validate_revision(self):
		if not self.revision_of:
			if self.revision_reason:
				frappe.throw(_("Revision Reason can only be set for a quotation revision."))
			return

		if self.revision_of == self.name:
			frappe.throw(_("A quotation cannot be a revision of itself."))
		if not (self.revision_reason or "").strip():
			frappe.throw(_("Revision Reason is required for a controlled revision."))
		if not frappe.db.exists("Transport Quotation", self.revision_of):
			frappe.throw(_("The source Transport Quotation does not exist."))

		source = frappe.db.get_value(
			"Transport Quotation",
			self.revision_of,
			["docstatus", "customer"],
			as_dict=True,
		)
		if source.docstatus != 1:
			frappe.throw(_("A controlled revision must refer to an approved Transport Quotation."))
		if self.customer and source.customer != self.customer:
			frappe.throw(_("A revision must keep the source quotation's customer."))

		existing_revisions = frappe.get_all(
			"Transport Quotation",
			filters={"revision_of": self.revision_of, "docstatus": 0},
			pluck="name",
			limit=0,
		)
		if any(name != self.name for name in existing_revisions):
			frappe.throw(_("Another draft revision already exists for this quotation."))

	def validate_materials_and_locations(self):
		material_names = [row.material for row in self.materials if row.material]
		if len(material_names) != len(set(material_names)):
			frappe.throw(_("A material can only be added once to a quotation."))

		material_set = set(material_names)
		for material in material_names:
			active = frappe.db.get_value("Cargo Types", material, "active")
			if active is None:
				frappe.throw(_("Material {0} does not exist.").format(material))
			if not active:
				frappe.throw(_("Material {0} is inactive.").format(material))

		location_keys = set()
		for row in self.locations:
			if not row.material or row.material not in material_set:
				frappe.throw(_("Each selected location must belong to a material on this quotation."))
			if row.location_role not in {"Loading", "Destination"}:
				frappe.throw(_("Invalid location role on row {0}.").format(row.idx))

			key = (row.material, row.location_role, row.location)
			if key in location_keys:
				frappe.throw(_("A location can only be selected once per material and role."))
			location_keys.add(key)

			location_values = frappe.db.get_value(
				"Transport Location",
				row.location,
				["active", "location_usage"],
				as_dict=True,
			)
			if not location_values:
				frappe.throw(_("Transport Location {0} does not exist.").format(row.location))
			if not location_values.active:
				frappe.throw(_("Transport Location {0} is inactive.").format(row.location))

			allowed_usage = {"Loading", "Both"} if row.location_role == "Loading" else {"Unloading", "Both"}
			if location_values.location_usage not in allowed_usage:
				frappe.throw(
					_("Transport Location {0} cannot be used as a {1}.").format(
						row.location, row.location_role
					)
				)

		if self.is_submit_action() or self.is_send_to_customer_action():
			if not material_names:
				frappe.throw(_("Add at least one material before approving the quotation."))
			for material in material_names:
				roles = {row.location_role for row in self.locations if row.material == material}
				if not {"Loading", "Destination"}.issubset(roles):
					frappe.throw(
						_("Material {0} must have at least one loading point and one destination.").format(
							material
						)
					)

	def validate_rates(self, require_complete=False):
		selected_locations = {
			(row.material, row.location_role, row.location)
			for row in self.locations
		}
		route_periods = {}
		rated_loadings = set()
		rated_destinations = set()

		for row in self.rates:
			if not row.material or row.material not in {item.material for item in self.materials}:
				frappe.throw(_("Each rate must refer to a material on this quotation."))
			if (row.material, "Loading", row.loading_location) not in selected_locations:
				frappe.throw(_("Rate row {0} uses a loading point not selected for its material.").format(row.idx))
			if (row.material, "Destination", row.unloading_location) not in selected_locations:
				frappe.throw(_("Rate row {0} uses a destination not selected for its material.").format(row.idx))
			if row.loading_location == row.unloading_location:
				frappe.throw(_("Loading Point and Destination must be different on rate row {0}.").format(row.idx))

			if not row.effective_from or not row.effective_to:
				frappe.throw(_("Both effective dates are required on rate row {0}.").format(row.idx))
			effective_from = getdate(row.effective_from)
			effective_to = getdate(row.effective_to)
			if effective_to < effective_from:
				frappe.throw(_("Effective To cannot be before Effective From on rate row {0}.").format(row.idx))
			if self.service_period_from and effective_from < getdate(self.service_period_from):
				frappe.throw(_("Rate row {0} starts before the Transport Service Period.").format(row.idx))
			if self.service_period_to and effective_to > getdate(self.service_period_to):
				frappe.throw(_("Rate row {0} ends after the Transport Service Period.").format(row.idx))

			rate_value = flt(row.rate, 6)
			if not isfinite(rate_value) or rate_value <= 0:
				frappe.throw(_("Rate must be a positive finite amount on row {0}.").format(row.idx))

			route = (row.material, row.loading_location, row.unloading_location)
			for previous_from, previous_to in route_periods.setdefault(route, []):
				if effective_from <= previous_to and effective_to >= previous_from:
					frappe.throw(
						_("Rate periods overlap for Material {0}, Loading {1}, and Destination {2}.").format(
							row.material, row.loading_location, row.unloading_location
						)
					)
			route_periods[route].append((effective_from, effective_to))
			rated_loadings.add((row.material, row.loading_location))
			rated_destinations.add((row.material, row.unloading_location))

		if require_complete:
			if not self.rates:
				frappe.throw(_("Add at least one date-effective rate before approving the quotation."))
			for location in self.locations:
				if location.location_role == "Loading" and (
					location.material, location.location
				) not in rated_loadings:
					frappe.throw(
						_("Loading Point {0} has no rate assignment.").format(location.location)
					)
				if location.location_role == "Destination" and (
					location.material, location.location
				) not in rated_destinations:
					frappe.throw(
						_("Destination {0} has no rate assignment.").format(location.location)
					)

	def validate_approval_record(self):
		if not self.customer_approval_date:
			frappe.throw(_("Customer Approval Date is required before approving the quotation."))
		approval_date = getdate(self.customer_approval_date)
		if approval_date < getdate(self.quotation_date):
			frappe.throw(_("Customer Approval Date cannot be before the Quotation Date."))
		if approval_date > getdate(self.valid_until):
			frappe.throw(_("Customer Approval Date cannot be after Acceptance Valid Until."))
		if approval_date > getdate(today()):
			frappe.throw(_("Customer Approval Date cannot be in the future."))

	def validate_approved_immutability(self):
		if self.docstatus != 1:
			return
		previous = self.get_doc_before_save()
		if not previous or previous.docstatus != 1:
			return
		for fieldname in APPROVAL_IMMUTABLE_FIELDS:
			if self.get(fieldname) != previous.get(fieldname):
				frappe.throw(_("Approved Transport Quotations are immutable; create a controlled revision."))

	def validate_rejected_immutability(self):
		if self.docstatus != 0 or getattr(self.flags, "in_lifecycle_transition", False):
			return
		previous = self.get_doc_before_save()
		if previous and previous.status == "Rejected":
			frappe.throw(_("Rejected Transport Quotations cannot be modified; create a new quotation instead."))


def check_lifecycle_authorization(action_label: str):
	if frappe.session.user != "Administrator" and not (APPROVAL_ROLES & set(frappe.get_roles())):
		frappe.throw(
			_("You are not authorized to {0}.").format(action_label),
			frappe.PermissionError,
		)


@frappe.whitelist()
def send_quotation_to_customer(name: str, customer_note: str | None = None):
	check_lifecycle_authorization(_("send quotation to customer"))
	if not name or not frappe.db.exists("Transport Quotation", name):
		frappe.throw(_("Transport Quotation {0} does not exist.").format(name or ""))

	doc = frappe.get_doc("Transport Quotation", name)
	doc.check_permission("write")

	if doc.docstatus != 0 or doc.status not in {"Draft", "Pending Approval"}:
		frappe.throw(
			_("Only Draft or Pending Approval quotations can be sent to the customer (current status: {0}).").format(
				doc.status
			)
		)

	note = (customer_note or "").strip()
	if note:
		doc.customer_approval_notes = note

	doc.flags.in_lifecycle_transition = True
	doc.flags.in_send_to_customer = True
	doc.status = "Pending Approval"
	doc.save()

	doc.add_comment(
		"Info",
		_("Quotation sent to customer (Pending Approval) by {0}{1}").format(
			frappe.session.user, f": {note}" if note else "."
		),
	)
	return doc.as_dict()


@frappe.whitelist()
def approve_quotation(
	name: str,
	approval_date: str,
	approval_reference: str | None = None,
	approval_notes: str | None = None,
):
	check_lifecycle_authorization(_("record customer approval"))
	if not name or not frappe.db.exists("Transport Quotation", name):
		frappe.throw(_("Transport Quotation {0} does not exist.").format(name or ""))

	doc = frappe.get_doc("Transport Quotation", name)
	doc.check_permission("write")
	doc.check_permission("submit")

	if doc.docstatus != 0 or doc.status not in {"Draft", "Pending Approval"}:
		frappe.throw(
			_("Only Draft or Pending Approval quotations can be approved (current status: {0}).").format(
				doc.status
			)
		)

	doc.customer_approval_date = approval_date
	if approval_reference is not None and approval_reference.strip():
		doc.customer_approval_reference = approval_reference.strip()
	if approval_notes is not None and approval_notes.strip():
		doc.customer_approval_notes = approval_notes.strip()

	doc.flags.in_lifecycle_transition = True
	doc.save()
	doc.submit()
	return doc.as_dict()


@frappe.whitelist()
def reject_quotation(name: str, rejection_reason: str | None = None):
	check_lifecycle_authorization(_("record customer rejection"))
	if not name or not frappe.db.exists("Transport Quotation", name):
		frappe.throw(_("Transport Quotation {0} does not exist.").format(name or ""))

	reason = (rejection_reason or "").strip()
	if not reason:
		frappe.throw(_("Rejection Reason is required to reject a quotation."))

	doc = frappe.get_doc("Transport Quotation", name)
	doc.check_permission("write")

	if doc.docstatus == 1 or doc.status == "Approved":
		frappe.throw(_("Approved Transport Quotations cannot be marked as Rejected."))
	if doc.docstatus == 2 or doc.status == "Cancelled":
		frappe.throw(_("Cancelled Transport Quotations cannot be marked as Rejected."))
	if doc.status == "Rejected":
		frappe.throw(_("Transport Quotation {0} is already marked as Rejected.").format(doc.name))

	doc.customer_approval_notes = reason
	doc.flags.in_lifecycle_transition = True
	doc.status = "Rejected"
	doc.save()

	doc.add_comment(
		"Info",
		_("Customer rejection recorded by {0}: {1}").format(frappe.session.user, reason),
	)
	return doc.as_dict()


@frappe.whitelist()
def get_quotation_list_with_summaries(limit_page_length: int = 500):
	if not frappe.has_permission("Transport Quotation", "read"):
		frappe.throw(_("Not permitted to read Transport Quotations."), frappe.PermissionError)

	quotations = frappe.get_list(
		"Transport Quotation",
		fields=[
			"name",
			"customer",
			"quotation_date",
			"valid_until",
			"status",
			"docstatus",
			"owner",
			"modified",
		],
		order_by="creation desc",
		limit_page_length=int(limit_page_length or 500),
	)
	if not quotations:
		return []

	names = [q.name for q in quotations]
	materials = frappe.get_all(
		"Transport Quotation Material",
		filters={"parent": ["in", names], "parenttype": "Transport Quotation"},
		fields=["parent", "material", "idx"],
		order_by="idx asc",
		limit_page_length=0,
	)
	locations = frappe.get_all(
		"Transport Quotation Location",
		filters={"parent": ["in", names], "parenttype": "Transport Quotation"},
		fields=["parent", "material", "location_role", "location", "idx"],
		order_by="idx asc",
		limit_page_length=0,
	)
	rates = frappe.get_all(
		"Transport Quotation Rate",
		filters={"parent": ["in", names], "parenttype": "Transport Quotation"},
		fields=[
			"parent",
			"name",
			"material",
			"loading_location",
			"unloading_location",
			"rate",
			"effective_from",
			"effective_to",
			"rate_group",
			"idx",
		],
		order_by="idx asc",
		limit_page_length=0,
	)

	mat_by_parent: dict[str, list] = {}
	for row in materials:
		mat_by_parent.setdefault(row.parent, []).append({"material": row.material})

	loc_by_parent: dict[str, list] = {}
	for row in locations:
		loc_by_parent.setdefault(row.parent, []).append(
			{
				"material": row.material,
				"location_role": row.location_role,
				"location": row.location,
			}
		)

	rate_by_parent: dict[str, list] = {}
	for row in rates:
		rate_by_parent.setdefault(row.parent, []).append(
			{
				"name": row.name,
				"material": row.material,
				"loading_location": row.loading_location,
				"unloading_location": row.unloading_location,
				"rate": row.rate,
				"effective_from": str(row.effective_from) if row.effective_from else "",
				"effective_to": str(row.effective_to) if row.effective_to else "",
				"rate_group": row.rate_group,
			}
		)

	result = []
	for q in quotations:
		item = dict(q)
		item["quotation_date"] = str(q.quotation_date) if q.quotation_date else ""
		item["valid_until"] = str(q.valid_until) if q.valid_until else ""
		item["modified"] = str(q.modified) if q.modified else ""
		item["materials"] = mat_by_parent.get(q.name, [])
		item["locations"] = loc_by_parent.get(q.name, [])
		item["rates"] = rate_by_parent.get(q.name, [])
		result.append(item)

	return result

