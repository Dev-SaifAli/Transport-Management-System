# Copyright (c) 2026, Al Rana Transport LLC and Contributors
# License: MIT. See LICENSE

"""Login page controller for the AL RANA Transport Management re-skin.

This app ships its own ``www/login.html`` template which overrides Frappe's
stock one. Because Frappe binds a ``www`` template to its co-located
``www/login.py`` controller, the override needs its own controller module that
delegates to Frappe's original one so every context flag used by the template
(``social_login``, ``provider_logins``, ``ldap_settings``, ``login_with_email_link``,
``login_label``, ``disable_signup``, ``disable_user_pass_login``, ``logo``,
``app_name``, ``signup_form_template``, ``show_footer_on_login``, ...) keeps being
populated exactly as before.

No login behaviour is changed here - the template only re-skins the layout.
"""

from __future__ import annotations

import datetime

import frappe.www.login as frappe_login


def get_context(context):
	# Reuse Frappe's own login context. This keeps the redirect for
	# already-authenticated users, the sanitised `?redirect-to=` handling and
	# every feature flag (signup / social login / LDAP / email link / 2FA)
	# intact.
	context.update(frappe_login.get_context(context))

	# `show_footer_on_login` drives whether Frappe's own web footer is shown on
	# this page. Force it off so the page renders as a clean full-bleed split
	# screen; other web pages are unaffected because this controller only runs
	# for the /login route.
	context.show_footer_on_login = False

	# Footer copyright year for the re-skinned panel.
	context["al_current_year"] = datetime.date.today().year

	return context
