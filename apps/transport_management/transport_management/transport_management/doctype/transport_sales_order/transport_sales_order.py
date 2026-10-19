# Copyright (c) 2026, Digital Data Enterprises and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

from transport_management.loading_stops import validate_loading_stop_rows

TON_UOM = "TON"
FIXED_ORDER_MODE = "Fixed Quantity"
QUOTATION_ORDER_MODE = "Quotation-backed Open"
MANUAL_RATE_OVERRIDE_ROLES = {"Transport Manager", "Transport Admin", "System Manager"}
BILLING_STATUS_NOT_READY = "Not Ready"
BILLING_STATUS_READY = "Ready for Billing"
BILLING_STATUS_IN_PROGRESS = "Billing In Progress"
BILLING_STATUS_INVOICED = "Invoiced"
BILLING_ROLES = {"Transport Manager", "Transport Admin", "System Manager"}
BILLING_READY_TRIP_STATUS = "CLOSED"
BILLING_ACTIVE_TRIP_STATUSES = {"PLANNED", "ASSIGNED", "LOADED", "IN_TRANSIT"}


class TransportSalesOrder(Document):
	def before_validate(self):
		if not self.order_mode:
			self.order_mode = FIXED_ORDER_MODE
		if not self.posting_date:
			self.posting_date = today()
		if not self.currency:
			self.currency = "AED"

		if self.order_mode == FIXED_ORDER_MODE:
			self.sync_loading_stops()
			self.calculate_totals()
		else:
			self.ordered_quantity = 0
			self.net_amount = 0
		self.set_conversion_status()
		self.set_billing_progress()

	def validate(self):
		self.validate_customer()
		self.validate_order_mode()
		if self.order_mode == QUOTATION_ORDER_MODE:
			self.validate_quotation_order()
			self.ordered_quantity = 0
			self.net_amount = 0
		else:
			self.validate_items(require_complete=self.is_submit_action())
			self.validate_loading_stops()
			self.calculate_totals(require_rates=self.is_submit_action())
		self.set_conversion_status()
		self.set_billing_progress()

	def before_submit(self):
		if self.order_mode == QUOTATION_ORDER_MODE:
			self.validate_quotation_order()
		else:
			self.validate_items(require_complete=True)
			self.calculate_totals(require_rates=True)
		self.status = "Submitted"

	def on_submit(self):
		frappe.db.set_value(self.doctype, self.name, "status", "Submitted", update_modified=False)

	def before_cancel(self):
		active_jobs = get_active_linked_jobs(self.name)
		if active_jobs:
			frappe.throw(
				_("Cannot cancel Sales Order {0} because active Transport Jobs exist: {1}.").format(
					self.name,
					", ".join(active_jobs),
				)
			)

	def on_cancel(self):
		frappe.db.set_value(self.doctype, self.name, "status", "Cancelled", update_modified=False)

	def is_submit_action(self):
		return getattr(self, "_action", None) == "submit" or self.docstatus == 1

	def validate_order_mode(self):
		if self.order_mode not in {FIXED_ORDER_MODE, QUOTATION_ORDER_MODE}:
			frappe.throw(_("Invalid Transport Sales Order mode {0}.").format(self.order_mode))

	def validate_quotation_order(self):
		if not self.transport_quotation:
			frappe.throw(_("Quotation-backed orders must reference an approved Transport Quotation."))
		if self.items:
			frappe.throw(_("Quotation-backed orders use rate snapshots, not fixed-quantity item rows."))
		if self.loading_stops:
			frappe.throw(_("Quotation-backed orders cannot use fixed-quantity loading stop rows."))
		if self.currency != "AED":
			frappe.throw(_("Quotation-backed Transport Sales Orders use AED."))

		quotation = frappe.get_doc("Transport Quotation", self.transport_quotation)
		if quotation.docstatus != 1 or quotation.status != "Approved":
			frappe.throw(_("Transport Sales Order can only be created from an approved, submitted Transport Quotation."))
		if quotation.customer != self.customer:
			frappe.throw(_("Transport Sales Order customer must match the Transport Quotation customer."))

		source_rates = {row.name: row for row in quotation.rates}
		if not self.rate_snapshots:
			frappe.throw(_("Add at least one selected quotation rate to the Transport Sales Order."))

		materials = {row.material for row in quotation.materials}
		locations = {
			(row.material, row.location_role, row.location)
			for row in quotation.locations
		}
		snapshot_names = set()
		route_periods = {}
		for snapshot in self.rate_snapshots:
			source = source_rates.get(snapshot.source_quotation_rate)
			if not source:
				frappe.throw(
					_("Rate snapshot row {0} does not reference a rate on the selected Transport Quotation.").format(
						snapshot.idx
					)
				)
			if snapshot.source_quotation_rate in snapshot_names:
				frappe.throw(_("A quotation rate can only be snapshotted once."))
			snapshot_names.add(snapshot.source_quotation_rate)

			if snapshot.material not in materials:
				frappe.throw(_("Rate snapshot material is not selected on the Transport Quotation."))
			if (snapshot.material, "Loading", snapshot.loading_location) not in locations:
				frappe.throw(_("Rate snapshot loading point is not permitted by the Transport Quotation."))
			if (snapshot.material, "Destination", snapshot.unloading_location) not in locations:
				frappe.throw(_("Rate snapshot destination is not permitted by the Transport Quotation."))
			if (
				snapshot.material != source.material
				or snapshot.loading_location != source.loading_location
				or snapshot.unloading_location != source.unloading_location
				or getdate(snapshot.effective_from) != getdate(source.effective_from)
				or getdate(snapshot.effective_to) != getdate(source.effective_to)
				or snapshot.currency != quotation.currency
				or flt(snapshot.rate, 6) != flt(source.rate, 6)
			):
				frappe.throw(_("Rate snapshot row {0} does not match its approved quotation rate.").format(snapshot.idx))

			route = (snapshot.material, snapshot.loading_location, snapshot.unloading_location)
			start = getdate(snapshot.effective_from)
			end = getdate(snapshot.effective_to)
			for previous_start, previous_end in route_periods.setdefault(route, []):
				if start <= previous_end and end >= previous_start:
					frappe.throw(
						_("Rate snapshot periods overlap for Material {0}, Loading {1}, and Destination {2}.").format(
							snapshot.material,
							snapshot.loading_location,
							snapshot.unloading_location,
						)
					)
			route_periods[route].append((start, end))

		# Validate geographical area (area_zone from Transport Location)
		loading_locations = {snapshot.loading_location for snapshot in self.rate_snapshots if snapshot.loading_location}
		loc_areas = {}
		if loading_locations:
			loc_records = frappe.get_all(
				"Transport Location",
				filters={"name": ["in", list(loading_locations)]},
				fields=["name", "area_zone"],
			)
			loc_areas = {r.name: (r.area_zone or "").strip() for r in loc_records}

		areas = set()
		for snapshot in self.rate_snapshots:
			area = loc_areas.get(snapshot.loading_location)
			if not area:
				frappe.throw(
					_("Loading location {0} does not have a geographical area (area_zone) configured.").format(
						snapshot.loading_location
					),
					frappe.ValidationError,
				)
			areas.add(area)

		if len(areas) > 1:
			frappe.throw(
				_("A Transport Sales Order must belong to a single geographical area, but selected rates span multiple areas: {0}.").format(
					", ".join(sorted(areas))
				),
				frappe.ValidationError,
			)

		single_area = areas.pop()
		if self.get("area_zone") and self.get("area_zone") != single_area:
			frappe.throw(
				_("Sales Order area_zone '{0}' does not match the rate geographical area '{1}'.").format(
					self.get("area_zone"), single_area
				),
				frappe.ValidationError,
			)
		self.area_zone = single_area

		# Prevent duplicate conversion of the same quotation rate into active Sales Orders
		source_rate_names = [s.source_quotation_rate for s in self.rate_snapshots if s.source_quotation_rate]
		if source_rate_names:
			existing_active = frappe.db.sql(
				"""
				SELECT
					child.source_quotation_rate,
					parent.name as sales_order
				FROM `tabTransport Sales Order Rate Snapshot` child
				INNER JOIN `tabTransport Sales Order` parent ON parent.name = child.parent
				WHERE child.parenttype = 'Transport Sales Order'
				  AND parent.docstatus < 2
				  AND parent.name != %s
				  AND child.source_quotation_rate IN ({0})
				""".format(", ".join(["%s"] * len(source_rate_names))),
				[self.name or ""] + source_rate_names,
				as_dict=True,
			)
			if existing_active:
				conflict = existing_active[0]
				frappe.throw(
					_("Quotation rate {0} has already been converted in active Sales Order {1}.").format(
						conflict.source_quotation_rate, conflict.sales_order
					),
					frappe.ValidationError,
				)

		self.validate_submitted_quotation_commercials_immutable()

	def validate_submitted_quotation_commercials_immutable(self):
		if self.is_new() or self.docstatus != 1:
			return
		previous = self.get_doc_before_save()
		if not previous or previous.docstatus != 1:
			return
		if (
			previous.order_mode != self.order_mode
			or previous.transport_quotation != self.transport_quotation
			or quotation_rate_snapshot_values(previous) != quotation_rate_snapshot_values(self)
		):
			frappe.throw(
				_("Submitted quotation-backed Transport Sales Order rates are immutable.")
			)

	def validate_customer(self):
		if self.customer and not frappe.db.exists("Customer", self.customer):
			frappe.throw(_("Customer {0} does not exist.").format(self.customer))

	def validate_items(self, require_complete=False):
		if require_complete and not self.items:
			frappe.throw(_("Sales Order must have at least one item row."))

		for row in self.items:
			validate_ton_uom(row.uom)
			self.validate_item_row(row, require_complete=require_complete)

	def validate_item_row(self, row, require_complete=False):
		quantity = flt(row.quantity, 6)
		if not isfinite(quantity) or quantity <= 0:
			frappe.throw(_("Quantity must be greater than zero on row {0}.").format(row.idx))

		if require_complete:
			for fieldname, label in (
				("material", _("Item / Material")),
				("loading_location", _("Loading Point")),
				("unloading_location", _("Unloading Point")),
			):
				if not row.get(fieldname):
					frappe.throw(_("{0} is required on row {1}.").format(label, row.idx))

		if row.material:
			validate_active_material(row.material)
		if row.loading_location:
			validate_location_usage(row.loading_location, {"Loading", "Both"}, _("Loading Point"))
		if row.unloading_location:
			validate_location_usage(row.unloading_location, {"Unloading", "Both"}, _("Unloading Point"))
		if row.loading_location and row.loading_location == row.unloading_location:
			frappe.throw(_("Loading Point and Unloading Point must be different on row {0}.").format(row.idx))
		if row.transport_job and not frappe.db.exists("Transport Job", row.transport_job):
			frappe.throw(_("Transport Job {0} linked on row {1} does not exist.").format(row.transport_job, row.idx))
		if row.manual_rate_override:
			validate_manual_rate_override_permission()

	def sync_loading_stops(self):
		if not self.loading_stops:
			return

		items_by_idx = {row.idx: row for row in self.items}
		for stop in self.loading_stops:
			if not stop.item_idx and len(self.items) == 1:
				stop.item_idx = 1

			item = items_by_idx.get(stop.item_idx)
			if item:
				stop.sales_order_item = item.name

		for item_idx, stops in self.get_loading_stops_by_item_idx().items():
			item = items_by_idx.get(item_idx)
			if item and stops:
				item.loading_location = stops[0].loading_location

	def validate_loading_stops(self):
		if not self.loading_stops:
			return

		items_by_idx = {row.idx: row for row in self.items}
		for item_idx, stops in self.get_loading_stops_by_item_idx().items():
			item = items_by_idx.get(item_idx)
			if not item:
				frappe.throw(_("Loading stop row references missing Sales Order item row {0}.").format(item_idx))
			validate_loading_stop_rows(stops, item.quantity, _("Sales Order item row {0}").format(item_idx))

	def get_loading_stops_by_item_idx(self):
		grouped = {}
		for stop in self.loading_stops or []:
			if not stop.item_idx:
				frappe.throw(_("Item Row is required on loading stop row {0}.").format(stop.idx))
			grouped.setdefault(stop.item_idx, []).append(stop)
		return grouped

	def calculate_totals(self, require_rates=False):
		net_amount = 0
		ordered_quantity = 0
		for row in self.items:
			if not row.uom:
				row.uom = TON_UOM
			validate_ton_uom(row.uom)

			if row.manual_rate_override:
				validate_manual_rate_override_permission()
				validate_manual_rate(row.rate, row.idx)
				row.rate_source = "Manual Override"
			elif self.can_resolve_rate(row):
				row.rate = resolve_transport_rate(
					self.customer,
					row.material,
					row.loading_location,
					row.unloading_location,
					self.posting_date,
					raise_if_missing=require_rates,
				)
				row.rate_source = "Transport Rate" if row.rate else ""
			elif require_rates:
				raise_missing_rate(row, self.customer)

			if require_rates and (row.rate is None or row.rate == ""):
				raise_missing_rate(row, self.customer)

			row.amount = flt(row.quantity, 6) * flt(row.rate, 6)
			net_amount += flt(row.amount, 6)
			ordered_quantity += flt(row.quantity, 6)

		self.net_amount = net_amount
		self.ordered_quantity = ordered_quantity

	def set_billing_progress(self):
		if not self.name:
			self.delivered_quantity = 0
			self.billing_status = BILLING_STATUS_NOT_READY
			return
		self.delivered_quantity = get_sales_order_delivered_quantity(self.name)
		self.billing_status = evaluate_sales_order_billing_status(self.name)

	def can_resolve_rate(self, row):
		return all((
			self.customer,
			self.posting_date,
			row.material,
			row.loading_location,
			row.unloading_location,
		))

	def set_conversion_status(self):
		if self.docstatus == 2:
			self.status = "Cancelled"
			return
		if self.docstatus == 0:
			self.status = "Draft"
			return
		if self.order_mode == QUOTATION_ORDER_MODE:
			all_materials = {row.material for row in self.rate_snapshots if row.material}
			all_snapshot_names = {row.name for row in self.rate_snapshots}
			active_jobs = frappe.get_all(
				"Transport Job",
				filters={"sales_order": self.name, "quantity_mode": "Open", "status": ["!=", "Cancelled"]},
				fields=["name", "material"],
				limit_page_length=0,
			)
			if not active_jobs:
				self.status = "Submitted"
				return

			converted_snapshot_names = set(
				frappe.db.sql_list(
					"""
					SELECT DISTINCT snap.sales_order_rate_snapshot
					FROM `tabTransport Job Rate Snapshot` snap
					INNER JOIN `tabTransport Job` job ON job.name = snap.parent
					WHERE job.sales_order = %s
					  AND job.quantity_mode = 'Open'
					  AND job.status != 'Cancelled'
					""",
					(self.name,),
				)
			)
			converted_materials = {job.material for job in active_jobs if job.material}
			if (all_snapshot_names and all_snapshot_names.issubset(converted_snapshot_names)) or (
				all_materials and all_materials.issubset(converted_materials)
			):
				self.status = "Converted"
			else:
				self.status = "Partially Converted"
			return

		converted = [row for row in self.items if row.converted or row.transport_job]
		if not converted:
			self.status = "Submitted"
		elif len(converted) == len(self.items):
			self.status = "Converted"
		else:
			self.status = "Partially Converted"


@frappe.whitelist()
def get_transport_rate(customer, material, loading_location, unloading_location, posting_date):
	"""Return the active customer/material/route rate for the given order date."""
	return resolve_transport_rate(
		customer,
		material,
		loading_location,
		unloading_location,
		posting_date,
		raise_if_missing=True,
	)


@frappe.whitelist()
def create_quotation_transport_sales_order(quotation, quotation_rate_names=None, area_zone=None):
	if not frappe.has_permission("Transport Sales Order", "create"):
		frappe.throw(_("You do not have permission to create Transport Sales Orders."), frappe.PermissionError)
	if not quotation or not frappe.db.exists("Transport Quotation", quotation):
		frappe.throw(_("Transport Quotation must exist."))

	# Concurrency lock on quotation to serialize conversions and prevent race conditions
	frappe.db.sql(
		"SELECT name FROM `tabTransport Quotation` WHERE name = %s FOR UPDATE",
		quotation,
	)

	source = frappe.get_doc("Transport Quotation", quotation)
	source.check_permission("read")
	if source.docstatus != 1 or source.status != "Approved":
		frappe.throw(_("Only an approved, submitted Transport Quotation can create a Transport Sales Order."))
	if not source.rates:
		frappe.throw(_("The approved Transport Quotation has no rates to snapshot."))

	# Resolve geographical areas for loading points
	loading_locations = {row.loading_location for row in source.rates if row.loading_location}
	loc_areas = {}
	if loading_locations:
		loc_records = frappe.get_all(
			"Transport Location",
			filters={"name": ["in", list(loading_locations)]},
			fields=["name", "area_zone"],
		)
		loc_areas = {r.name: (r.area_zone or "").strip() for r in loc_records}

	# Verify all loading locations have an area_zone configured
	for row in source.rates:
		if not loc_areas.get(row.loading_location):
			frappe.throw(
				_("Loading location {0} does not have a geographical area (area_zone) configured.").format(
					row.loading_location
				)
			)

	source_rates = {row.name: row for row in source.rates}
	all_areas = sorted({loc_areas[row.loading_location] for row in source.rates})

	if area_zone:
		area_zone = str(area_zone).strip()
		rates_in_area = [row for row in source.rates if loc_areas.get(row.loading_location) == area_zone]
		if not rates_in_area:
			frappe.throw(
				_("No rates found in Transport Quotation {0} for geographical area {1}.").format(
					source.name, area_zone
				)
			)
		candidates = rates_in_area
	else:
		candidates = list(source.rates)

	selected_names = parse_quotation_rate_names(quotation_rate_names)
	if selected_names is not None:
		if not selected_names:
			frappe.throw(_("Select at least one quotation rate for the Transport Sales Order."))
		missing_names = selected_names - set(source_rates)
		if missing_names:
			frappe.throw(
				_("Selected rate {0} does not belong to Transport Quotation {1}.").format(
					", ".join(sorted(missing_names)),
					source.name,
				)
			)
		selected_rates = [row for row in candidates if row.name in selected_names]
		if not selected_rates:
			frappe.throw(
				_("None of the selected quotation rates match geographical area {0}.").format(area_zone)
			)
	else:
		if not area_zone and len(all_areas) > 1:
			frappe.throw(
				_("This quotation contains rates across multiple geographical areas ({0}). Please specify an area_zone to create an area-wise Sales Order.").format(
					", ".join(all_areas)
				)
			)
		selected_rates = candidates

	# Ensure selected rates belong to exactly one area
	selected_areas = {loc_areas[row.loading_location] for row in selected_rates}
	if len(selected_areas) > 1:
		frappe.throw(
			_("A Transport Sales Order must belong to a single geographical area, but selected rates span multiple areas: {0}.").format(
				", ".join(sorted(selected_areas))
			)
		)
	resolved_area = selected_areas.pop()

	order = frappe.new_doc("Transport Sales Order")
	order.update({
		"order_mode": QUOTATION_ORDER_MODE,
		"transport_quotation": source.name,
		"posting_date": today(),
		"customer": source.customer,
		"area_zone": resolved_area,
		"currency": "AED",
		"estimated_quantity": source.estimated_quantity,
		"estimated_trips": source.estimated_trips,
		"remarks": source.remarks,
	})
	for row in selected_rates:
		order.append("rate_snapshots", {
			"source_quotation_rate": row.name,
			"material": row.material,
			"loading_location": row.loading_location,
			"unloading_location": row.unloading_location,
			"effective_from": row.effective_from,
			"effective_to": row.effective_to,
			"currency": source.currency,
			"rate": row.rate,
		})
	order.insert()
	return order.name


@frappe.whitelist()
def get_quotation_sales_order_summary(quotation):
	"""Return area-wise breakdown of quotation rates, materials, loading/destination points,
	and existing linked active Sales Orders."""
	if not quotation or not frappe.db.exists("Transport Quotation", quotation):
		frappe.throw(_("Transport Quotation must exist."))

	source = frappe.get_doc("Transport Quotation", quotation)
	source.check_permission("read")

	# Fetch existing active sales orders and their rate snapshots
	active_snapshots = frappe.db.sql(
		"""
		SELECT
			child.source_quotation_rate,
			parent.name as sales_order,
			parent.status,
			parent.docstatus,
			parent.creation
		FROM `tabTransport Sales Order Rate Snapshot` child
		INNER JOIN `tabTransport Sales Order` parent ON parent.name = child.parent
		WHERE child.parenttype = 'Transport Sales Order'
		  AND parent.transport_quotation = %s
		  AND parent.docstatus < 2
		ORDER BY parent.creation asc
		""",
		source.name,
		as_dict=True,
	)
	snapshot_so_map = {}
	for row in active_snapshots:
		snapshot_so_map[row.source_quotation_rate] = {
			"sales_order": row.sales_order,
			"status": row.status,
			"docstatus": row.docstatus,
		}

	# Resolve area_zone for each loading location
	loading_locations = {row.loading_location for row in source.rates if row.loading_location}
	loc_areas = {}
	if loading_locations:
		loc_records = frappe.get_all(
			"Transport Location",
			filters={"name": ["in", list(loading_locations)]},
			fields=["name", "area_zone"],
		)
		loc_areas = {r.name: (r.area_zone or "").strip() for r in loc_records}

	# Group rates by area_zone
	areas_dict = {}
	for row in source.rates:
		area = loc_areas.get(row.loading_location) or "Unassigned Area"
		if area not in areas_dict:
			areas_dict[area] = {
				"area_zone": area,
				"has_valid_area": bool(loc_areas.get(row.loading_location)),
				"rates": [],
				"materials": set(),
				"loading_locations": set(),
				"unloading_locations": set(),
				"sales_orders": {},
			}
		rate_info = {
			"name": row.name,
			"material": row.material,
			"loading_location": row.loading_location,
			"unloading_location": row.unloading_location,
			"effective_from": str(row.effective_from),
			"effective_to": str(row.effective_to),
			"rate": flt(row.rate, 6),
			"converted_sales_order": snapshot_so_map.get(row.name),
		}
		areas_dict[area]["rates"].append(rate_info)
		areas_dict[area]["materials"].add(row.material)
		areas_dict[area]["loading_locations"].add(row.loading_location)
		areas_dict[area]["unloading_locations"].add(row.unloading_location)
		if row.name in snapshot_so_map:
			so = snapshot_so_map[row.name]
			areas_dict[area]["sales_orders"][so["sales_order"]] = so

	areas_list = []
	for area_name, data in sorted(areas_dict.items()):
		converted_count = sum(1 for r in data["rates"] if r["converted_sales_order"])
		total_count = len(data["rates"])
		areas_list.append({
			"area_zone": data["area_zone"],
			"has_valid_area": data["has_valid_area"],
			"total_rates": total_count,
			"converted_rates": converted_count,
			"is_fully_converted": converted_count == total_count and total_count > 0,
			"is_partially_converted": 0 < converted_count < total_count,
			"materials": sorted(list(data["materials"])),
			"loading_locations": sorted(list(data["loading_locations"])),
			"unloading_locations": sorted(list(data["unloading_locations"])),
			"sales_orders": list(data["sales_orders"].values()),
			"rates": data["rates"],
		})

	total_areas = len(areas_list)
	converted_areas = sum(1 for a in areas_list if a["is_fully_converted"])

	return {
		"quotation": source.name,
		"customer": source.customer,
		"status": source.status,
		"docstatus": source.docstatus,
		"total_areas": total_areas,
		"converted_areas": converted_areas,
		"has_unconverted_areas": converted_areas < total_areas,
		"areas": areas_list,
	}


def parse_quotation_rate_names(rate_names):
	if rate_names in (None, ""):
		return None
	if isinstance(rate_names, str):
		try:
			rate_names = frappe.parse_json(rate_names)
		except ValueError:
			rate_names = [rate_names]
	if not isinstance(rate_names, (list, tuple, set)):
		frappe.throw(_("Selected quotation rates must be a list of rate row names."))
	names = [str(name) for name in rate_names if name]
	if len(names) != len(set(names)):
		frappe.throw(_("A quotation rate cannot be selected more than once."))
	return set(names)


@frappe.whitelist()
def resolve_quotation_sales_order_rate(
	sales_order,
	material,
	loading_location,
	unloading_location,
	loading_date,
	allow_unresolved=False,
):
	if not sales_order or not frappe.db.exists("Transport Sales Order", sales_order):
		frappe.throw(_("Transport Sales Order must exist."))
	order = frappe.get_doc("Transport Sales Order", sales_order)
	order.check_permission("read")
	if order.docstatus != 1 or order.order_mode != QUOTATION_ORDER_MODE:
		frappe.throw(_("Rate resolution requires a submitted quotation-backed Transport Sales Order."))
	if not all((material, loading_location, unloading_location, loading_date)):
		frappe.throw(_("Material, loading point, destination, and loading date are required to resolve a rate."))

	rate_date = getdate(loading_date)
	matches = [
		row
		for row in order.rate_snapshots
		if row.material == material
		and row.loading_location == loading_location
		and row.unloading_location == unloading_location
		and getdate(row.effective_from) <= rate_date <= getdate(row.effective_to)
	]
	if not matches:
		if allow_unresolved:
			return {
				"blocked_reason": _("No approved quotation rate covers this route on loading date {0}.").format(
					rate_date
				)
			}
		frappe.throw(_("No approved quotation rate covers this route on loading date {0}.").format(rate_date))
	if len(matches) > 1:
		if allow_unresolved:
			return {
				"blocked_reason": _("Multiple approved quotation rates cover this route on loading date {0}.").format(
					rate_date
				)
			}
		frappe.throw(_("Multiple approved quotation rates cover this route on loading date {0}.").format(rate_date))
	row = matches[0]
	return {
		"rate_snapshot": row.name,
		"source_quotation_rate": row.source_quotation_rate,
		"material": row.material,
		"loading_location": row.loading_location,
		"unloading_location": row.unloading_location,
		"effective_from": row.effective_from,
		"effective_to": row.effective_to,
		"currency": row.currency,
		"rate": flt(row.rate, 6),
	}


def resolve_transport_rate(
	customer,
	material,
	loading_location,
	unloading_location,
	posting_date,
	raise_if_missing=True,
):
	if not all((customer, material, loading_location, unloading_location, posting_date)):
		frappe.throw(_("Customer, Material, Loading, Unloading, and Date are required to resolve rate."))

	rates = frappe.db.sql(
		"""
		select name, rate
		from `tabTransport Rate`
		where customer = %(customer)s
			and material = %(material)s
			and loading_location = %(loading_location)s
			and unloading_location = %(unloading_location)s
			and active = 1
			and valid_from <= %(posting_date)s
			and (valid_to is null or valid_to = '' or %(posting_date)s <= valid_to)
		order by valid_from desc, creation desc
		""",
		{
			"customer": customer,
			"material": material,
			"loading_location": loading_location,
			"unloading_location": unloading_location,
			"posting_date": getdate(posting_date),
		},
		as_dict=True,
	)

	if len(rates) > 1:
		frappe.throw(_("Multiple active transport rates found for this customer, material, and route."))
	if not rates:
		if not raise_if_missing:
			return None
		frappe.throw(
			_(
				"No active transport rate found for Customer {0}, Material {1}, Loading {2}, Unloading {3}."
			).format(customer, material, loading_location, unloading_location)
		)
	return flt(rates[0].rate, 6)


def quotation_rate_snapshot_values(doc):
	return [
		(
			row.source_quotation_rate,
			row.material,
			row.loading_location,
			row.unloading_location,
			row.effective_from,
			row.effective_to,
			row.currency,
			flt(row.rate, 6),
		)
		for row in doc.rate_snapshots
	]


@frappe.whitelist()
def create_transport_jobs(sales_order, row_names=None):
	"""Create one Transport Job per selected submitted Sales Order row."""
	selected_rows = parse_row_names(row_names)
	doc = frappe.get_doc("Transport Sales Order", sales_order)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Transport Jobs can only be created from a submitted Sales Order."))
	if not frappe.has_permission("Transport Job", "create"):
		frappe.throw(_("You do not have permission to create Transport Jobs."))

	if doc.order_mode == QUOTATION_ORDER_MODE:
		return create_open_quotation_jobs(doc, selected_rows)

	rows = get_rows_for_conversion(doc, selected_rows)
	if not rows:
		frappe.throw(_("No unconverted Sales Order rows were selected."))

	created_jobs = []
	for row in rows:
		created_jobs.append(create_transport_job_from_row(doc, row))

	update_conversion_status(doc.name)
	return created_jobs


def create_open_quotation_jobs(doc, selected_snapshot_names=None):
	lock_sales_order(doc.name)
	doc.reload()
	if doc.docstatus != 1 or doc.order_mode != QUOTATION_ORDER_MODE:
		frappe.throw(_("Open Transport Jobs require a submitted quotation-backed Transport Sales Order."))
	if not doc.transport_quotation or not frappe.db.exists("Transport Quotation", doc.transport_quotation):
		frappe.throw(_("Quotation-backed Transport Sales Order must retain its source Transport Quotation."))

	groups = get_quotation_job_groups(doc.rate_snapshots)
	if selected_snapshot_names is not None:
		known_snapshot_names = {row.name for row in doc.rate_snapshots}
		known_materials = {row.material for row in doc.rate_snapshots if row.material}
		is_material_selection = bool(selected_snapshot_names and selected_snapshot_names.issubset(known_materials))
		if not is_material_selection:
			unknown = selected_snapshot_names - known_snapshot_names
			if unknown:
				frappe.throw(
					_("Selected rate snapshot {0} does not belong to Transport Sales Order {1}.").format(
						", ".join(sorted(unknown)),
						doc.name,
					)
				)
			groups = {
				material: snapshots
				for material, snapshots in groups.items()
				if any(row.name in selected_snapshot_names for row in snapshots)
			}
		else:
			groups = {
				material: snapshots
				for material, snapshots in groups.items()
				if material in selected_snapshot_names
			}
	if not groups:
		frappe.throw(_("No quotation-backed material groups were selected."))

	created_jobs = []
	for material, snapshots in groups.items():
		existing_jobs = frappe.get_all(
			"Transport Job",
			filters={
				"sales_order": doc.name,
				"quantity_mode": "Open",
				"material": material,
				"status": ["!=", "Cancelled"],
			},
			pluck="name",
			limit_page_length=2,
		)
		if existing_jobs:
			if selected_snapshot_names is not None:
				frappe.throw(
					_("A Transport Job already exists for Material {0} on Transport Sales Order {1}: {2}.").format(
						material,
						doc.name,
						", ".join(existing_jobs),
					)
				)
			continue

		job = frappe.new_doc("Transport Job")
		job.update({
			"customer": doc.customer,
			"requested_date": doc.posting_date,
			"quantity_mode": "Open",
			"requested_quantity": 0,
			"uom": TON_UOM,
			"material": material,
			"unloading_site": snapshots[0].unloading_location,
			"loading_site": snapshots[0].loading_location,
			"sales_order": doc.name,
			"transport_quotation": doc.transport_quotation,
			"customer_lpo_number": doc.customer_lpo_number,
			"sale_order_reference": doc.name,
			"agreed_rate": 0,
			"ordered_amount": 0,
			"special_instructions": doc.remarks,
		})
		loading_points = []
		for snapshot in snapshots:
			job.append("sales_order_rate_snapshots", {
				"sales_order_rate_snapshot": snapshot.name,
			})
			if snapshot.loading_location and snapshot.loading_location not in loading_points:
				loading_points.append(snapshot.loading_location)
		for loading_point in loading_points:
			job.append("permitted_loading_points", {
				"loading_location": loading_point,
			})
		job.insert()
		created_jobs.append(job.name)

	if not created_jobs:
		frappe.throw(
			_("All quotation-backed materials for Transport Sales Order {0} have already been converted into Transport Jobs.").format(
				doc.name
			)
		)

	update_conversion_status(doc.name)
	return created_jobs


def get_quotation_job_groups(rate_snapshots):
	groups = {}
	for snapshot in rate_snapshots or []:
		if not snapshot.material:
			continue
		groups.setdefault(snapshot.material, []).append(snapshot)
	return groups


def parse_row_names(row_names):
	if not row_names:
		return None
	if isinstance(row_names, str):
		row_names = frappe.parse_json(row_names)
	if isinstance(row_names, str):
		row_names = [row_names]
	return set(row_names)


def get_rows_for_conversion(doc, selected_rows):
	rows = []
	for row in doc.items:
		if selected_rows and row.name not in selected_rows:
			continue
		if row.converted or row.transport_job:
			frappe.throw(_("Sales Order row {0} is already converted.").format(row.idx))
		rows.append(row)
	return rows


def create_transport_job_from_row(doc, row):
	lock_sales_order_item(row.name)
	child_state = frappe.db.get_value(
		"Transport Sales Order Item",
		row.name,
		["converted", "transport_job"],
		as_dict=True,
	)
	if child_state.converted or child_state.transport_job:
		frappe.throw(_("Sales Order row {0} is already converted.").format(row.idx))

	existing_job = frappe.db.get_value(
		"Transport Job",
		{"sales_order": doc.name, "sales_order_item": row.name},
		"name",
	)
	if existing_job:
		frappe.db.set_value(
			"Transport Sales Order Item",
			row.name,
			{"transport_job": existing_job, "converted": 1},
			update_modified=False,
		)
		return existing_job

	job = frappe.new_doc("Transport Job")
	job.update({
		"customer": doc.customer,
		"requested_date": doc.posting_date,
		"loading_site": row.loading_location,
		"unloading_site": row.unloading_location,
		"material": row.material,
		"requested_quantity": row.quantity,
		"uom": TON_UOM,
		"sales_order": doc.name,
		"sales_order_item": row.name,
		"customer_lpo_number": doc.customer_lpo_number,
		"sale_order_reference": doc.name,
		"agreed_rate": row.rate,
		"ordered_amount": row.amount,
		"special_instructions": doc.remarks,
	})
	copy_sales_order_loading_stops_to_job(doc, row, job)
	job.insert()

	frappe.db.set_value(
		"Transport Sales Order Item",
		row.name,
		{"transport_job": job.name, "converted": 1},
		update_modified=False,
	)
	return job.name


def copy_sales_order_loading_stops_to_job(doc, row, job):
	stops = [
		stop
		for stop in doc.get("loading_stops") or []
		if stop.item_idx == row.idx or stop.sales_order_item == row.name
	]
	for stop in stops:
		job.append("loading_stops", {
			"loading_location": stop.loading_location,
			"planned_quantity": stop.planned_quantity,
			"notes": stop.get("notes"),
		})


def lock_sales_order_item(row_name):
	if not frappe.db.sql(
		"select name from `tabTransport Sales Order Item` where name = %s for update",
		row_name,
	):
		frappe.throw(_("Sales Order row {0} does not exist.").format(row_name))


def lock_sales_order(sales_order):
	if not frappe.db.sql(
		"select name from `tabTransport Sales Order` where name = %s for update",
		sales_order,
	):
		frappe.throw(_("Transport Sales Order {0} does not exist.").format(sales_order))


def update_conversion_status(sales_order):
	doc = frappe.get_doc("Transport Sales Order", sales_order)
	doc.set_conversion_status()
	doc.set_billing_progress()
	frappe.db.set_value(
		"Transport Sales Order",
		sales_order,
		{"status": doc.status, "delivered_quantity": doc.delivered_quantity, "billing_status": doc.billing_status},
		update_modified=False,
	)


def refresh_sales_order_billing_progress(sales_order):
	if not sales_order or not frappe.db.exists("Transport Sales Order", sales_order):
		return
	values = {
		"delivered_quantity": get_sales_order_delivered_quantity(sales_order),
		"billing_status": evaluate_sales_order_billing_status(sales_order),
	}
	frappe.db.set_value("Transport Sales Order", sales_order, values, update_modified=False)


def get_sales_order_delivered_quantity(sales_order):
	result = frappe.db.sql(
		"""
		select coalesce(sum(delivered_quantity), 0)
		from `tabTransport Job`
		where sales_order = %s
			and status != 'Cancelled'
		""",
		(sales_order,),
	)
	return flt(result[0][0] if result else 0, 6)


def evaluate_sales_order_billing_status(sales_order):
	if frappe.db.get_value("Transport Sales Order", sales_order, "order_mode") == QUOTATION_ORDER_MODE:
		if frappe.db.exists(
			"Sales Invoice",
			{
				"transport_sales_order": sales_order,
				"tms_invoice_type": "Transport",
				"docstatus": 0,
			},
		):
			return BILLING_STATUS_IN_PROGRESS

		job_names = frappe.get_all(
			"Transport Job",
			filters={"sales_order": sales_order, "status": ["!=", "Cancelled"]},
			pluck="name",
		)
		if job_names and frappe.db.exists(
			"Transport Trip",
			{"transport_job": ["in", job_names], "transport_billing_status": "Draft Invoice"},
		):
			return BILLING_STATUS_IN_PROGRESS

		from transport_management.transport_management.doctype.transport_job.transport_job import (
			get_open_order_billable_trips,
		)

		if get_open_order_billable_trips(sales_order=sales_order):
			return BILLING_STATUS_READY
		trips = frappe.get_all(
			"Transport Trip",
			filters={"transport_job": ["in", job_names], "status": ["!=", "CANCELLED"]},
			fields=["transport_billing_status"],
		) if job_names else []
		if any(trip.transport_billing_status != "Invoiced" for trip in trips):
			return BILLING_STATUS_NOT_READY
		if frappe.db.exists(
			"Sales Invoice",
			{
				"transport_sales_order": sales_order,
				"tms_invoice_type": "Transport",
				"docstatus": 1,
			},
		) or any(trip.transport_billing_status == "Invoiced" for trip in trips):
			return BILLING_STATUS_INVOICED
		return BILLING_STATUS_NOT_READY

	invoice = get_active_transport_invoice_for_sales_order(sales_order)
	if invoice:
		if invoice.docstatus == 0:
			return BILLING_STATUS_IN_PROGRESS
		if invoice.docstatus == 1:
			return BILLING_STATUS_INVOICED

	jobs = get_sales_order_jobs(sales_order)
	if not jobs:
		return BILLING_STATUS_NOT_READY

	for job in jobs:
		if flt(job.remaining_quantity, 6) != 0:
			return BILLING_STATUS_NOT_READY
		if flt(job.delivered_quantity, 6) <= 0:
			return BILLING_STATUS_NOT_READY

	trips = frappe.get_all(
		"Transport Trip",
		filters={"transport_job": ["in", [job.name for job in jobs]], "status": ["!=", "CANCELLED"]},
		fields=["name", "status"],
	)
	if not trips:
		return BILLING_STATUS_NOT_READY
	if any(trip.status in BILLING_ACTIVE_TRIP_STATUSES or trip.status == "EXCEPTION" for trip in trips):
		return BILLING_STATUS_NOT_READY
	if any(trip.status != BILLING_READY_TRIP_STATUS for trip in trips):
		return BILLING_STATUS_NOT_READY

	return BILLING_STATUS_READY


def get_active_transport_invoice_for_sales_order(sales_order):
	invoice_name = frappe.db.get_value("Transport Sales Order", sales_order, "transport_sales_invoice")
	filters = {
		"transport_sales_order": sales_order,
		"tms_invoice_type": "Transport",
		"docstatus": ["<", 2],
	}
	if invoice_name:
		rows = frappe.get_all(
			"Sales Invoice",
			filters={**filters, "name": invoice_name},
			fields=["name", "docstatus"],
			order_by="creation desc",
			limit=1,
		)
		if rows:
			return rows[0]
	rows = frappe.get_all("Sales Invoice", filters=filters, fields=["name", "docstatus"], order_by="creation desc", limit=1)
	return rows[0] if rows else None


def get_sales_order_jobs(sales_order):
	return frappe.get_all(
		"Transport Job",
		filters={"sales_order": sales_order, "status": ["!=", "Cancelled"]},
		fields=[
			"name",
			"sales_order_item",
			"material",
			"loading_site",
			"unloading_site",
			"requested_quantity",
			"delivered_quantity",
			"remaining_quantity",
			"status",
			"agreed_rate",
		],
		order_by="creation asc",
	)


@frappe.whitelist()
def prepare_billing(sales_order):
	if not sales_order or not frappe.db.exists("Transport Sales Order", sales_order):
		frappe.throw(_("Transport Sales Order must exist."))
	if not _user_can_prepare_billing():
		frappe.throw(_("You are not permitted to prepare Transport Sales Order billing."), frappe.PermissionError)
	refresh_sales_order_billing_progress(sales_order)
	billing_status = frappe.db.get_value("Transport Sales Order", sales_order, "billing_status")
	if billing_status != BILLING_STATUS_READY:
		frappe.throw(_("Transport Sales Order {0} is not ready for billing.").format(sales_order))
	return {
		"transport_sales_order": sales_order,
		"billing_status": billing_status,
		"route": ["Form", "Sales Invoice", "new-sales-invoice"],
	}


def _user_can_prepare_billing(user=None):
	user = user or frappe.session.user
	return bool(BILLING_ROLES.intersection(frappe.get_roles(user)))


def get_active_linked_jobs(sales_order):
	return frappe.get_all(
		"Transport Job",
		filters={
			"sales_order": sales_order,
			"status": ["!=", "Cancelled"],
		},
		pluck="name",
	)


def validate_ton_uom(uom):
	if uom != TON_UOM:
		frappe.throw(_("UOM must be TON."))


def validate_manual_rate_override_permission():
	if MANUAL_RATE_OVERRIDE_ROLES.intersection(set(frappe.get_roles())):
		return
	frappe.throw(_("You are not permitted to override Transport Rates manually."))


def validate_manual_rate(rate, row_idx):
	rate = flt(rate, 6)
	if not isfinite(rate) or rate <= 0:
		frappe.throw(_("Manual Rate must be greater than zero on row {0}.").format(row_idx))


def validate_active_material(material):
	active = frappe.db.get_value("Cargo Types", material, "active")
	if active is None:
		frappe.throw(_("Material {0} does not exist.").format(material))
	if not active:
		frappe.throw(_("Material {0} must be active.").format(material))


def validate_location_usage(location, allowed_usages, label):
	if not frappe.db.exists("Transport Location", location):
		frappe.throw(_("{0} must be a valid Transport Location.").format(label))

	values = frappe.db.get_value(
		"Transport Location",
		location,
		["location_usage", "active"],
		as_dict=True,
	)
	if not values.active:
		frappe.throw(_("{0} must be an active Transport Location.").format(label))
	if values.location_usage not in allowed_usages:
		frappe.throw(
			_("{0} must have Location Usage {1}.").format(
				label,
				_(" or ").join(sorted(allowed_usages)),
			)
		)


def raise_missing_rate(row, customer):
	frappe.throw(
		_(
			"No active transport rate found for Customer {0}, Material {1}, Loading {2}, Unloading {3}."
		).format(customer, row.material, row.loading_location, row.unloading_location)
	)


def ensure_ton_uom():
	if frappe.db.exists("UOM", TON_UOM):
		return TON_UOM
	uom = frappe.new_doc("UOM")
	uom.uom_name = TON_UOM
	uom.enabled = 1
	uom.insert(ignore_permissions=True)
	return uom.name
