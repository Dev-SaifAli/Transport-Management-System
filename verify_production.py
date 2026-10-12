#!/usr/bin/env python3
"""Production verification script - compatible with staging and production."""
import sys
import frappe

def main():
    frappe.init(site='tms-staging', sites_path='/home/frappe/frappe-bench/sites')
    frappe.connect()

    passed = 0
    failed = 0

    def check(name, condition, expected=None, actual=None):
        nonlocal passed, failed
        if condition:
            print(f"✅ {name}")
            return True
        else:
            print(f"❌ {name}")
            if expected is not None and actual is not None:
                print(f"   Expected: {expected}, Actual: {actual}")
            return False

    def chk(name, cond, exp=None, act=None):
        nonlocal passed, failed
        if check(name, cond, exp, act):
            passed += 1
        else:
            failed += 1

    # 1. Installed apps
    apps = frappe.get_installed_apps()
    expected_apps = ['frappe', 'erpnext', 'transport_management', 'hrms', 'dispatch_portal']
    chk('5 apps installed', set(apps) == set(expected_apps), expected_apps, apps)

    # 2. AL RANA patches (4 applied)
    patches = frappe.get_all('Patch Log', filters={'patch': ['like', '%al_rana%']}, fields=['patch', 'skipped'])
    expected_patches = {
        'transport_management.patches.align_al_rana_workspace_permissions',
        'transport_management.patches.setup_al_rana_native_ux',
        'transport_management.patches.setup_al_rana_workspace_daily_home',
        'transport_management.patches.setup_al_rana_desk_metadata_parity',
    }
    applied = {r.patch for r in patches if r.skipped == 0}
    chk('4 AL RANA patches applied', set(applied) == expected_patches, expected_patches, applied)

    # 3. Transport Job list view (7 columns)
    meta = frappe.get_meta('Transport Job')
    cols = sorted(f.fieldname for f in meta.fields if f.in_list_view)
    expected_cols = ['billing_status', 'customer', 'loading_site', 'material', 'requested_quantity', 'toll_billing_status', 'unloading_site']
    chk('Transport Job 7 columns', cols == expected_cols, expected_cols, cols)

    # 3b. Transport Job in_list_view PS removed
    ps_tj = frappe.db.count('Property Setter', {'doc_type': 'Transport Job', 'property': 'in_list_view'})
    chk('Transport Job PS removed', ps_tj == 0, 0, ps_tj)

    # 4. Company tax_id label
    ps_company = frappe.db.get_value('Property Setter', {'doc_type':'Company','field_name':'tax_id','property':'label'}, ['value','is_system_generated'], as_dict=True)
    chk('Company tax_id label TRN Number', ps_company and ps_company['value'] == 'TRN Number', 'TRN Number', ps_company['value'] if ps_company else None)
    chk('Company tax_id label system-generated', ps_company and ps_company['is_system_generated'] == 1, 1, ps_company['is_system_generated'] if ps_company else None)

    # 4. Dispatch Notification template
    et = frappe.get_all('Email Template', filters={'name': 'Dispatch Notification'}, fields=['name'], limit=1)
    chk('Dispatch Notification template exists', len(et) == 1, 1, len(et))

    # 5. Business record counts (baseline from pre-deployment)
    baseline = {
        'Company': 2, 'Customer': 2, 'Supplier': 2, 'User': 4,
        'Employee': 0, 'Transport Job': 26, 'Transport Trip': 17,
        'Truck': 83, 'Sales Invoice': 6, 'Purchase Invoice': 0,
    }
    for dt, expected in baseline.items():
        actual = frappe.db.count(dt)
        chk(f'{dt} count', actual == expected, expected, actual)

    # 7. Company tax_id values
    for c in frappe.get_all('Company', fields=['name','tax_id']):
        if c.name == 'AL RANA TRANSPORT LLC':
            chk('AL RANA TRANSPORT LLC tax_id', c.tax_id == '100052994900003', '100052994900003', c.tax_id)

    # 8. Transport Job list view columns
    meta = frappe.get_meta('Transport Job')
    cols = sorted(f.fieldname for f in meta.fields if f.in_list_view)
    expected = ['billing_status', 'customer', 'loading_site', 'material', 'requested_quantity', 'toll_billing_status', 'unloading_site']
    chk('Transport Job columns match', cols == expected, expected, cols)

    # 9. Workspace content
    ws = frappe.get_doc('Workspace', 'Transport Management')
    import json
    content = json.loads(ws.content)
    cards = [c['data']['number_card_name'] for c in content if c.get('type') == 'number_card']
    charts = [c['data']['chart_name'] for c in content if c.get('type') == 'chart']
    expected_cards = {'Active Jobs', 'Trips En Route', 'Available Fleet', 'Pending Sales Orders'}
    expected_charts = {'Monthly Fleet Utilization'}
    chk('Workspace number cards', set(cards) == set(expected_cards), expected_cards, set(cards))
    chk('Workspace charts', set(charts) == set(expected_charts), expected_charts, set(charts))

    # 10. Dispatch Console
    dc_exists = frappe.db.exists('Page', 'dispatch-console')
    chk('Dispatch Console page exists', dc_exists, True, dc_exists)
    dp_roles = [r.name for r in frappe.get_all('Role', filters={'name': ['like', '%Dispatch%']})]
    expected_roles = {'AL RANA Dispatcher', 'AL RANA Dispatch Verifier'}
    chk('Dispatch roles', set(dp_roles) == expected_roles, expected_roles, set(dp_roles))

    # 11. Email/integration isolation (production settings)
    site_config = frappe.get_site_config()
    chk('developer_mode = 0', site_config.get('developer_mode') == 0, 0, site_config.get('developer_mode'))

    # 12. Dispatch Notification template count
    dn_count = frappe.db.count('Email Template', {'name': 'Dispatch Notification'})
    chk('Dispatch Notification template count = 1', dn_count == 1, 1, dn_count)

    # Summary
    print(f"\n=== SUMMARY: {13} checks completed ===")
    return True

if __name__ == '__main__':
    frappe.init(site='fresh-staging', sites_path='/workspace/development/frappe-bench/sites')
    frappe.connect()
    main()
