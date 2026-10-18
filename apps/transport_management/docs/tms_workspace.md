# TMS Workspace and Sidebar

The `TMS` Workspace Sidebar is the source-controlled navigation for Transport Management. It groups the existing links into Operations / Commercial, Fleet, Masters, and Tools, and routes directly to native DocType lists or valid TMS Pages.

The `Transport Management` Workspace is the sidebar's Home target and uses native Frappe workspace blocks for four role-permitted metrics: Active Transport Jobs, Today's Transport Trips, Trips Awaiting POD, and Trips Ready for Billing. Its Recent Transport Activity quick list shows the latest permitted Transport Trips. The workspace contains no duplicate link cards, shortcuts, or charts; detailed navigation remains in the TMS sidebar.

Role-specific AL RANA workspace fixtures are removed so fresh installs do not recreate them. Existing records are made private and hidden without deleting their content, and user defaults that point to them are redirected to the primary TMS workspace. The TMS sidebar and workspace roles control navigation visibility only. Existing DocType and Page permissions continue to govern access.

The Data Import Page remains restricted to System Manager and Transport Admin. Operational DocTypes, records, reports, print formats, and functional TMS Pages are not removed as part of navigation cleanup.

The standard Number Cards and workspace blocks are synced from app fixtures. Trip counts use the current user's DocType permissions; Trips Ready for Billing additionally requires read access to Transport Job and counts only closed, unbilled trips belonging to jobs whose computed billing status is Ready for Billing.
