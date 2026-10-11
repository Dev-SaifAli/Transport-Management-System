# Owned Truck Master

The standalone TMS owns `Truck` as the canonical operational master for owned vehicles. This avoids creating a duplicate Truck or ERPNext Vehicle master while preserving existing table data and active fields for truck number, license plate, make, model, year, driver, fuel setup, odometer, status, documents, chassis, and engine.

`transport_management` owns the `Truck` DocType metadata and controller. Existing Truck records are preserved in `tabTruck` and backfilled to `ownership_type = OWN`.

Operational truck types for the current AL RANA phase are `TIPPER` and `TANKER`. Legacy source files may still say `BULKER`; imports normalize that term to canonical `TANKER` and do not store new `BULKER` links.

## Added Fields

- `vehicle_type`: optional Link to `Truck Type`
- `capacity`: optional payload capacity value
- `capacity_uom`: optional Link to `UOM`
- `ownership_type`: Select with `OWN`, default `OWN`
- `registration_number`: optional value when different from `license_plate`
- `registration_expiry`: optional Date
- `registration_attachment`: optional Attach field for the registration document
- `insurance_policy_number`: optional Data
- `insurance_expiry`: optional Date
- `insurance_attachment`: optional Attach field for the insurance document
- `other_document_attachment`: optional Attach field for any other truck document
- `erpnext_asset`: optional Link to ERPNext `Asset`
- `remarks`: optional Small Text

## Document Model

The final TMS Truck document model uses native Frappe Attach fields directly on Truck:

- `registration_number`
- `registration_expiry`
- `registration_attachment`
- `insurance_policy_number`
- `insurance_expiry`
- `insurance_attachment`
- `other_document_attachment`

The legacy Fleet `vehicle_documents` child table is not part of the final TMS Truck design. `Document Attachments` and `Document Name` are no longer installed after Fleet removal.

## Asset Relationship

`Truck` is the operational TMS master used for dispatch and trip execution. ERPNext `Asset` remains the financial and depreciation master. The optional `erpnext_asset` link connects the two records without duplicating purchase, capitalization, depreciation, or accounting fields on Truck.

ERPNext `Vehicle` is not the TMS source of truth for this project because Transport Trip uses the TMS-owned `Truck` master for truck-specific operational fields.

## Driver Relationship

`Truck.trans_ms_driver` means the truck's default or home driver. `Transport Trip.driver` means the actual driver for that trip and remains authoritative during execution. The trip driver is not forced to match the truck default driver.

## Availability

For OWN trips, server-side validation requires the selected Truck to exist, have `disabled = 0`, and have `status = Idle`. Trucks with `Under Maintenance`, `On Trip`, or `Disabled` status are rejected. Dynamic status automation is intentionally deferred.

## Hired Trucks

Hired trucks are intentionally not stored in the owned Truck master. HIRED Transport Trips use `transporter`, linked `hired_vehicle` records from the Hired Vehicle master, and optional `hired_driver` text.

## Trailers

Trailers are out of scope for the current AL RANA Transport Management phase. Transport Management does not use trailer fields, and TMS-owned Truck metadata omits trailer fields unless a separate TMS trailer feature is approved.

## Deferred

This phase does not implement capacity-vs-trip validation, maintenance workflow, fuel workflow, document expiry reminders, GPS/geofencing, Asset creation, settlements, purchase invoices, or accounting automation.
