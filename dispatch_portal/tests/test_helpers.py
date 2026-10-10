"""Shared fixtures for the AL RANA Dispatch console tests.

Only real TMS DocTypes are used: Transport Job, Transport Trip, Transport
Location, Truck, Truck Driver and Transport Trip Document are all owned by
``transport_management``.  The console adds no business entity of its own.
"""

import frappe
from frappe.utils import now_datetime, today

DISPATCH_ROLE = "AL RANA Dispatcher"
VERIFIER_ROLE = "AL RANA Dispatch Verifier"

PREFIX = "DISPATCH-TEST"


def make_user(roles, first_name="Dispatch Tester"):
	email = f"{PREFIX.lower()}-{frappe.generate_hash(length=8).lower()}@al-rana-dispatch.test"
	user = frappe.get_doc({
		"doctype": "User",
		"email": email,
		"enabled": 1,
		"first_name": first_name,
		"send_welcome_email": 0,
		"new_password": "Dispatch#2026",
		"roles": [{"role": role} for role in roles],
	})
	user.insert(ignore_permissions=True)
	frappe.clear_cache(user=email)
	return email


def ensure_uom(uom="TON"):
	if not frappe.db.exists("UOM", uom):
		frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert(ignore_permissions=True)
	return uom


def ensure_truck_type(name="DISPATCH TEST TRUCK TYPE"):
	existing = frappe.get_all("Truck Type", filters={"truck_type": name}, pluck="name", limit=1)
	if existing:
		return existing[0]
	doc = frappe.get_doc({"doctype": "Truck Type", "truck_type": name})
	doc.insert(ignore_permissions=True)
	return doc.name


def ensure_material(name="DISPATCH TEST AGGREGATE"):
	existing = frappe.get_all("Cargo Types", filters={"cargo_name": name}, pluck="name", limit=1)
	if existing:
		return existing[0]
	doc = frappe.get_doc({"doctype": "Cargo Types", "cargo_name": name, "active": 1})
	doc.insert(ignore_permissions=True)
	return doc.name


def material_with_truck_type(name="DISPATCH TEST AGGREGATE"):
	"""A Cargo Types record that allows the test truck type, like real master data."""
	existing = frappe.get_all("Cargo Types", filters={"cargo_name": name}, pluck="name", limit=1)
	if existing:
		doc = frappe.get_doc("Cargo Types", existing[0])
	else:
		doc = frappe.get_doc({"doctype": "Cargo Types", "cargo_name": name, "active": 1})
		doc.insert(ignore_permissions=True)

	truck_type = ensure_truck_type()
	if truck_type not in {row.truck_type for row in doc.get("allowed_truck_types") or []}:
		doc.append("allowed_truck_types", {"truck_type": truck_type})
		doc.save(ignore_permissions=True)
	return doc.name


def ensure_country(country="United Arab Emirates"):
	if not frappe.db.exists("Country", country):
		frappe.get_doc({"doctype": "Country", "country_name": country}).insert(ignore_permissions=True)
	return country


def make_location(label, latitude, longitude, usage="Both"):
	name = f"{PREFIX} {label}"
	existing = frappe.get_all("Transport Location", filters={"location": name}, pluck="name", limit=1)
	if existing:
		return existing[0]

	doc = frappe.get_doc({
		"doctype": "Transport Location",
		"location": name,
		"country": ensure_country(),
		"location_type": "Plant",
		"location_usage": usage,
		"city": label,
		"latitude": latitude,
		"longitude": longitude,
		"active": 1,
	})
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.insert(ignore_permissions=True)
	return doc.name


def make_truck(number, status="Idle"):
	name = f"{PREFIX}-TRUCK-{number}"
	existing = frappe.get_all("Truck", filters={"truck_number": name}, pluck="name", limit=1)
	if existing:
		return existing[0]

	doc = frappe.get_doc({
		"doctype": "Truck",
		"license_plate": name,
		"truck_number": name,
		"status": status,
		"disabled": 0,
		"ownership_type": "OWN",
		"vehicle_type": ensure_truck_type(),
		"fuel_uom": ensure_uom("Litre"),
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def make_driver(number, cell=None):
	name = f"{PREFIX}-DRIVER-{number}"
	existing = frappe.get_all("Truck Driver", filters={"full_name": name}, pluck="name", limit=1)
	if existing:
		return existing[0]

	if not cell:
		cell = f"00{int(number):08d}"[-10:]

	doc = frappe.get_doc({
		"doctype": "Truck Driver",
		"full_name": name,
		"status": "Active",
		"cell_number": cell,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _non_group_value(doctype, label_field, preferred=None):
	"""Return a leaf/non-group value of a tree-ish DocType (Group/Territory)."""
	filters = {"is_group": 0}
	if preferred:
		existing = frappe.get_all(
			doctype, filters={label_field: preferred, "is_group": 0}, pluck="name", limit=1
		)
		if existing:
			return existing[0]

	values = frappe.get_all(doctype, filters=filters, pluck="name", limit=1)
	if values:
		return values[0]

	values = frappe.get_all(doctype, pluck="name", limit=1)
	return values[0] if values else None


def make_customer(name):
	existing = frappe.get_all("Customer", filters={"customer_name": name}, pluck="name", limit=1)
	if existing:
		return existing[0]

	doc = frappe.get_doc({
		"doctype": "Customer",
		"customer_name": name,
		"customer_group": _non_group_value("Customer Group", "customer_group_name", "Commercial"),
		"territory": _non_group_value("Territory", "territory_name"),
	})
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
	return doc.name


def make_job(customer, loading_site, unloading_site, quantity=100):
	doc = frappe.get_doc({
		"doctype": "Transport Job",
		"customer": customer,
		"requested_date": today(),
		"loading_site": loading_site,
		"unloading_site": unloading_site,
		"material": material_with_truck_type(),
		"requested_quantity": quantity,
		"uom": ensure_uom(),
		"status": "Ready",
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def make_trip(job, loading_site, unloading_site, quantity=40, status="PLANNED", vehicle=None, driver=None):
	doc = frappe.get_doc({
		"doctype": "Transport Trip",
		"transport_job": job,
		"trip_date": today(),
		"loading_site": loading_site,
		"unloading_site": unloading_site,
		"material": material_with_truck_type(),
		"planned_quantity": quantity,
		"uom": ensure_uom(),
		"execution_source": "OWN",
		"status": status,
		"vehicle": vehicle,
		"driver": driver,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def make_trip_document(trip, driver, document_type="ABER_TOLL", file_url="/files/dispatch-test-toll.pdf"):
	doc = frappe.get_doc({
		"doctype": "Transport Trip Document",
		"transport_trip": trip,
		"document_type": document_type,
		"file": file_url,
		"uploaded_by_driver": driver,
		"upload_source": "DRIVER_PORTAL",
		"ai_status": "PROCESSED",
		"ai_confidence": 91.5,
		"extracted_amount": 123.45,
		"extracted_ticket_number": "AI-GDN-0001",
		"extracted_receipt_number": "AI-RCPT-0001",
		"extracted_document_datetime": now_datetime(),
		"extracted_net_weight": 42.5,
		"extracted_customer": "AI EXTRACTED CUSTOMER",
		"verification_status": "PENDING_REVIEW",
	})
	doc.insert(ignore_permissions=True)
	return doc.name


class DispatchTestCase(frappe.tests.utils.FrappeTestCase):
	"""Base test case with a savepoint and the dispatch roles in place."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from dispatch_portal.services.dispatch_access import ensure_dispatch_roles

		ensure_dispatch_roles()

	def setUp(self):
		super().setUp()
		frappe.db.savepoint("dispatch_portal_test")
		self.loading_site = make_location("Dispatch Origin", 25.2048, 55.2708, "Loading")
		self.unloading_site = make_location("Dispatch Destination", 25.0761, 55.2261, "Unloading")
		self.customer = make_customer(f"{PREFIX} CUSTOMER")
		self.job = make_job(self.customer, self.loading_site, self.unloading_site)
		self.truck = make_truck("100")
		self.driver = make_driver("200")
		self.trip = make_trip(
			self.job,
			self.loading_site,
			self.unloading_site,
			vehicle=self.truck,
			driver=self.driver,
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="dispatch_portal_test")
		super().tearDown()

	def reload(self, doctype, name):
		return frappe.get_doc(doctype, name)
