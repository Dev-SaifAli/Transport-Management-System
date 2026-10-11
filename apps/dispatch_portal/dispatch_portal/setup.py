"""Idempotent AL RANA Dispatch installation and migration hooks."""

from __future__ import annotations

import frappe

from dispatch_portal.desk_setup import setup_dispatch_console
from dispatch_portal.services.dispatch_access import ensure_dispatch_roles


def after_install():
	ensure_dispatch_roles()
	setup_dispatch_console()


def after_migrate():
	ensure_dispatch_roles()
	setup_dispatch_console()
