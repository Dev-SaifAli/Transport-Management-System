app_name = "transport_management"
app_title = "Transport Management"
app_publisher = "Digital Data Enterprises"
app_description = "Transportation Management System for managing transport orders, shipments, vehicles, drivers, routes, and delivery operations"
app_email = "saif.ali@dgtdata.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "transport_management",
# 		"logo": "/assets/transport_management/logo.png",
# 		"title": "Transport Management",
# 		"route": "/transport_management",
# 		"has_permission": "transport_management.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/transport_management/css/transport_management.css"

# include js, css files in header of web template
# web_include_css = "/assets/transport_management/css/transport_management.css"
# web_include_js = "/assets/transport_management/js/transport_management.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "transport_management/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Sales Invoice": "public/js/sales_invoice.js",
}
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "transport_management/public/icons.svg"

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
# 	"methods": "transport_management.utils.jinja_methods",
# 	"filters": "transport_management.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "transport_management.install.before_install"
# after_install = "transport_management.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "transport_management.uninstall.before_uninstall"
# after_uninstall = "transport_management.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "transport_management.utils.before_app_install"
# after_app_install = "transport_management.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "transport_management.utils.before_app_uninstall"
# after_app_uninstall = "transport_management.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "transport_management.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "transport_management.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["transport_management.search.awesomebar_results"]

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

doc_events = {
	"Sales Invoice": {
		"on_update": "transport_management.transport_management.doctype.transport_job.transport_job.sync_transport_invoice_lifecycle",
		"on_submit": "transport_management.transport_management.doctype.transport_job.transport_job.sync_transport_invoice_lifecycle",
		"on_cancel": "transport_management.transport_management.doctype.transport_job.transport_job.sync_transport_invoice_lifecycle",
		"on_trash": "transport_management.transport_management.doctype.transport_job.transport_job.sync_transport_invoice_lifecycle",
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"transport_management.tasks.all"
# 	],
# 	"daily": [
# 		"transport_management.tasks.daily"
# 	],
# 	"hourly": [
# 		"transport_management.tasks.hourly"
# 	],
# 	"weekly": [
# 		"transport_management.tasks.weekly"
# 	],
# 	"monthly": [
# 		"transport_management.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "transport_management.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "transport_management.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "transport_management.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "transport_management.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["transport_management.utils.before_request"]
# after_request = ["transport_management.utils.after_request"]

# Job Events
# ----------
# before_job = ["transport_management.utils.before_job"]
# after_job = ["transport_management.utils.after_job"]

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
# 	"transport_management.auth.validate"
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


# Install upgrade-safe TMS customizations.
after_migrate = "transport_management.setup.after_migrate"
