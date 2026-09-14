# Fleet MS Dependency Boundary

`vsd_fleet_ms` has been removed from the site. The business-facing TMS workflow and selected former fleet masters are owned by `transport_management`.

## Canonical Workflow

Customer requirement -> Transport Job -> Transport Trip -> OWN or HIRED execution.

## Migrated Fleet Masters

- Truck
- Truck Driver
- Transport Location
- Cargo Types
- Truck Type

These masters are source-controlled in `transport_management` with the same DocType names and database tables. Fleet core JSON and controllers are not modified.

`Truck.fuel_uom` uses ERPNext `UOM`; legacy Fleet `Fuel UOM` is no longer installed.

Trailers are out of scope for the current AL RANA Transport Management phase. The legacy Fleet `Trailers` DocType is no longer installed. If trailer management is required later, it should be designed as a separate TMS feature rather than inheriting legacy Fleet behavior automatically.

Truck document storage is modeled with native TMS-owned Attach fields on `Truck`: `registration_attachment`, `insurance_attachment`, and `other_document_attachment`. The legacy Fleet `vehicle_documents` table and its `Document Attachments` / `Document Name` child DocTypes are no longer installed and are not part of the final TMS Truck design.

## Retired Legacy Workflow

The old Fleet workflow is not part of the active TMS product:

- Transportation Order compatibility
- Transport Assignments compatibility table installation
- Transportation Order UI customization
- Create Transport Shipment button
- Transport Shipment workflow
- Fleet Trips, Manifest, Trip Routes, Fuel Requests, Requested Payment

`Transport Shipment` metadata and any existing records are preserved only for historical readability. Its old Fleet references are stored as plain text values, not Links to Fleet DocTypes. It is not exposed in the Transport Management workspace/sidebar and should not receive new production behavior.

## Deferred

Rates, settlements, purchase invoices, accounting automation, route pricing, toll estimation, and Fleet workflow adapters are intentionally deferred.
