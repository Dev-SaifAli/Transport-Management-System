"""Single-site Railway WSGI entrypoint for Frappe.

Railway forwards requests with its public hostname as ``Host``. For this
deployment, ``FRAPPE_SITE`` is the authoritative site name.
"""

import os

import frappe.app

site = os.environ.get("FRAPPE_SITE")
sites_path = os.environ.get("SITES_PATH", "/home/frappe/frappe-bench/sites")

if not site:
	raise RuntimeError("FRAPPE_SITE is required")

frappe.app._site = site
frappe.app._sites_path = sites_path

application = frappe.app.application
