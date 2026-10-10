import frappe
import json

SIDEBAR = "ERPNext Modules"
APP = "transport_management"
HIDE_APPS = ["erpnext"]          # add "hrms" if you also want the HR tile hidden

MODULES = [
    "Selling", "Buying", "Stock", "Manufacturing", "Projects", "Assets",
    "Quality", "Subcontracting",
    "Invoicing", "Payments", "Financial Reports", "Taxes", "Banking",
    "Budget", "Accounts Setup", "Subscription", "Share Management",
    "Organization", "ERPNext Settings",
]

COPY_FIELDS = ["label", "link_type", "icon", "link_to", "url",
               "filters", "route_options", "navigate_to_tab"]


def arrange_desktop():
    ensure_module()
    build_workspace()
    build_sidebar()
    build_icon()
    hide_standard_icons()
    frappe.db.commit()
    frappe.clear_cache()


def ensure_module():
    if not frappe.db.exists("Module Def", SIDEBAR):
        frappe.get_doc({
            "doctype": "Module Def",
            "module_name": SIDEBAR,
            "app_name": APP,
        }).insert(ignore_permissions=True)


def build_workspace():
    # Landing page that the tile opens first. Same shape as the Transport Management workspace.
    content = json.dumps([
        {"id": "erpm_header", "type": "header",
         "data": {"text": '<span class="h4">ERPNext Modules</span>', "col": 12}},
        {"id": "erpm_spacer", "type": "spacer", "data": {"col": 12}},
        {"id": "erpm_text", "type": "paragraph",
         "data": {"text": "Use the sidebar on the left to open any ERPNext module.", "col": 12}},
    ])
    values = {
        "label": SIDEBAR,
        "title": SIDEBAR,
        "module": SIDEBAR,
        "app": APP,
        "type": "Workspace",
        "icon": "briefcase",
        "indicator_color": "blue",
        "public": 1,
        "is_hidden": 0,
        "content": content,
    }
    if frappe.db.exists("Workspace", SIDEBAR):
        doc = frappe.get_doc("Workspace", SIDEBAR)
        doc.update(values)
    else:
        doc = frappe.new_doc("Workspace")
        doc.update(values)
    doc.flags.ignore_permissions = True
    doc.save()


def build_sidebar():
    if frappe.db.exists("Workspace Sidebar", SIDEBAR):
        doc = frappe.get_doc("Workspace Sidebar", SIDEBAR)
        doc.items = []
    else:
        doc = frappe.new_doc("Workspace Sidebar")
        doc.title = SIDEBAR

    doc.header_icon = "briefcase"
    doc.module = SIDEBAR
    doc.standard = 0
    doc.app = APP

    # First item: link to our own workspace page (same pattern as Transport Management)
    doc.append("items", {
        "label": "Home",
        "type": "Link",
        "link_type": "Workspace",
        "link_to": SIDEBAR,
        "icon": "home",
        "child": 0,
        "indent": 0,
        "collapsible": 1,
    })

    for module in MODULES:
        if not frappe.db.exists("Workspace Sidebar", module):
            continue
        src = frappe.get_doc("Workspace Sidebar", module)

        doc.append("items", {
            "label": module,
            "type": "Section Break",
            "link_type": "DocType",
            "icon": src.header_icon,
            "indent": 1,
            "keep_closed": 1,
            "collapsible": 1,
            "child": 0,
        })

        for item in src.items:
            if item.type != "Link" or item.child:
                continue
            row = {f: item.get(f) for f in COPY_FIELDS}
            row.update({"type": "Link", "child": 1, "indent": 0, "collapsible": 1})
            doc.append("items", row)

    doc.flags.ignore_permissions = True
    doc.save()


def build_icon():
    values = {
        "icon_type": "Link",
        "link_type": "Workspace Sidebar",
        "link_to": SIDEBAR,
        "sidebar": SIDEBAR,
        "app": APP,
        "logo_url": "/assets/erpnext/images/erpnext-logo.svg",
        "standard": 0,
        "hidden": 0,
    }
    if frappe.db.exists("Desktop Icon", SIDEBAR):
        frappe.db.set_value("Desktop Icon", SIDEBAR, values, update_modified=False)
    else:
        icon = frappe.new_doc("Desktop Icon")
        icon.label = SIDEBAR
        icon.update(values)
        icon.insert(ignore_permissions=True)


def hide_standard_icons():
    names = frappe.get_all(
        "Desktop Icon",
        filters={"app": ["in", HIDE_APPS], "hidden": 0, "name": ["!=", SIDEBAR]},
        pluck="name",
    )
    for name in names:
        frappe.db.set_value("Desktop Icon", name, "hidden", 1, update_modified=False)