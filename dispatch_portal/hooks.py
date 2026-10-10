app_name = "dispatch_portal"
app_title = "AL RANA Dispatch"
app_publisher = "Digital Data Enterprises"
app_description = "AL RANA Dispatcher Console - dispatcher UI, API orchestration and role-aware access for the Transport Management System"
app_email = "saif.ali@dgtdata.com"
app_license = "mit"

# Apps
# ------------------

# AL RANA Dispatch is a thin console on top of the TMS: it never re-implements a
# transportation entity, every DocType it renders is owned by transport_management.
required_apps = ["transport_management"]

# Each item in the list will be shown as an app in the apps page
# This is the Frappe v16 mechanism that puts "AL RANA Dispatch" on the Desk app
# launcher as a dedicated, role-aware app icon that opens the dispatcher console.
add_to_apps_screen = [
	{
		"name": app_name,
		"logo": "/assets/dispatch_portal/icons/desktop_icons/solid/al_rana_dispatch.svg",
		"title": app_title,
		"route": "/app/dispatch-console",
		"has_permission": "dispatch_portal.api.permissions.has_console_access"
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/dispatch_portal/css/dispatch_portal.css"
# app_include_js = "/assets/dispatch_portal/js/dispatch_portal.js"

# include js, css files in header of web template
# web_include_css = "/assets/dispatch_portal/css/dispatch_portal.css"
# web_include_js = "/assets/dispatch_portal/js/dispatch_portal.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "dispatch_portal/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# The dispatcher console is a single Page (dispatch-console) whose sections are
# rendered by these modules; the page bootstrap lives in
# al_rana_dispatch/page/dispatch_console/dispatch_console.js
page_js = {
	"dispatch-console": [
		"public/js/dispatch_portal/console_common.js",
		"public/js/dispatch_portal/console_dashboard.js",
		"public/js/dispatch_portal/console_trips.js",
		"public/js/dispatch_portal/console_trip_map.js",
		"public/js/dispatch_portal/console_verification.js",
		"public/js/dispatch_portal/console_reports.js",
	]
}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "dispatch_portal/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "dispatch_portal.utils.jinja_methods",
# 	"filters": "dispatch_portal.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "dispatch_portal.install.before_install"
after_install = "dispatch_portal.setup.after_install"

# Uninstallation
# ------------

# before_uninstall = "dispatch_portal.uninstall.before_uninstall"
# after_uninstall = "dispatch_portal.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "dispatch_portal.utils.before_app_install"
# after_app_install = "dispatch_portal.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "dispatch_portal.utils.before_app_uninstall"
# after_app_uninstall = "dispatch_portal.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "dispatch_portal.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "dispatch_portal.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["dispatch_portal.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"dispatch_portal.tasks.all"
# 	],
# 	"daily": [
# 		"dispatch_portal.tasks.daily"
# 	],
# 	"hourly": [
# 		"dispatch_portal.tasks.hourly"
# 	],
# 	"weekly": [
# 		"dispatch_portal.tasks.weekly"
# 	],
# 	"monthly": [
# 		"dispatch_portal.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "dispatch_portal.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "dispatch_portal.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "dispatch_portal.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "dispatch_portal.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["dispatch_portal.utils.before_request"]
# after_request = ["dispatch_portal.utils.after_request"]

# Job Events
# ----------
# before_job = ["dispatch_portal.utils.before_job"]
# after_job = ["dispatch_portal.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"dispatch_portal.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# AL RANA Dispatch keeps owning its own registration: the app launcher icon, the
# dispatcher roles and the source-controlled Desktop Icon fixture must survive any
# transport_management migration and reinstall.
after_migrate = "dispatch_portal.setup.after_migrate"

