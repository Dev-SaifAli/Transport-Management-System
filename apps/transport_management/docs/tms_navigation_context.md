# TMS Navigation Context

Transport Management reuses standard ERPNext masters and TMS-owned fleet masters instead of duplicating party, vehicle, driver, and location records.

Native DocType list and form routes still belong to each DocType's owning module. For example, Customer belongs to Selling and Supplier belongs to Buying. To keep users oriented from the Transport Management workspace, reused masters open through lightweight Transport Management Desk Pages.

The wrapper pages provide:

- Transport Management context in the page title
- The underlying master name
- Open List
- Create New
- Back to Transport Management

The pages route to native Frappe list and form screens, so normal permissions and document behavior remain unchanged. They do not duplicate data or replace native list/form functionality.
