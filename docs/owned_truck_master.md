# Owned Truck Master

The standalone TMS reuses Fleet `Truck` as the canonical operational master for owned vehicles. This avoids creating a duplicate Truck or ERPNext Vehicle master while preserving existing Fleet fields for truck number, license plate, make, model, year, driver, fuel setup, odometer, status, documents, chassis, engine, and trailer reference.

`transport_management` extends `Truck` through idempotent Custom Fields installed from `after_migrate`; it does not edit `vsd_fleet_ms` DocType JSON or controller files. Existing Truck records are backfilled to `ownership_type = OWN`.

## Added Fields

- `vehicle_type`: optional Link to `Truck Type`
- `capacity`: optional payload capacity value
- `capacity_uom`: optional Link to `UOM`
- `ownership_type`: Select with `OWN`, default `OWN`
- `registration_number`: optional value when different from `license_plate`
- `registration_expiry`: optional Date
- `insurance_policy_number`: optional Data
- `insurance_expiry`: optional Date
- `erpnext_asset`: optional Link to ERPNext `Asset`
- `remarks`: optional Small Text

## Asset Relationship

`Truck` is the operational TMS master used for dispatch and trip execution. ERPNext `Asset` remains the financial and depreciation master. The optional `erpnext_asset` link connects the two records without duplicating purchase, capitalization, depreciation, or accounting fields on Truck.

ERPNext `Vehicle` is not the TMS source of truth for this project because Transport Trip already uses Fleet `Truck` and the Fleet app provides truck-specific operational fields.

## Driver Relationship

`Truck.trans_ms_driver` means the truck's default or home driver. `Transport Trip.driver` means the actual driver for that trip and remains authoritative during execution. The trip driver is not forced to match the truck default driver.

## Availability

For OWN trips, server-side validation requires the selected Truck to exist, have `disabled = 0`, and have `status = Idle`. Trucks with `Under Maintenance`, `On Trip`, or `Disabled` status are rejected. Dynamic status automation is intentionally deferred.

## Hired Trucks

Hired trucks are intentionally not stored in the owned Truck master. HIRED Transport Trips use `transporter`, linked `hired_vehicle` records from the Hired Vehicle master, and optional `hired_driver` text.

## Deferred

This phase does not implement capacity-vs-trip validation, maintenance workflow, fuel workflow, document expiry reminders, GPS/geofencing, Asset creation, settlements, purchase invoices, or accounting automation.
