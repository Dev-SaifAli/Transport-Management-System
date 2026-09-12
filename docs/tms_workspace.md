# Transport Management Workspace

The Transport Management workspace is the primary Desk navigation area for the standalone TMS. It is source-controlled in the transport_management app and synced by Frappe metadata migration.

## Sections

- Operations: Transport Job, Transport Trip
- Fleet: Owned Trucks, Hired Vehicle, Drivers, Trailers
- Masters: Customer, Suppliers / Transporters, Transport Location, Materials
- ERP: Sales Invoice, Purchase Invoice, Asset

Legacy Fleet workflows such as Manifest, legacy Trips, Trip Routes, Trip Locations, and deprecated Transport Shipment are intentionally not exposed as main TMS links.

## Number Cards

The workspace includes simple document-count cards for total jobs, active trips, in-transit trips, trips awaiting POD, and active hired vehicles. No report-backed KPIs are introduced in this phase.

## Reports

No TMS report links are added yet because dedicated standalone TMS reports have not been implemented. Report links should be added only when functional reports exist.
