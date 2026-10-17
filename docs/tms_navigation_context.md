# TMS Navigation Context

Transport Management reuses standard ERPNext masters and TMS-owned fleet masters instead of duplicating party, vehicle, driver, and location records.

Native DocType list and form routes still belong to each DocType's owning module. For example, Customer belongs to Selling and Supplier belongs to Buying. The TMS sidebar links directly to those native lists and to TMS-owned DocTypes, preserving standard Frappe routing and permission checks without wrapper pages.

Sidebar and workspace roles determine which navigation entries are presented; they do not grant access to records. Existing DocType and Page permissions remain authoritative.
