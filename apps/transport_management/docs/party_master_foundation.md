# Party Master Foundation

## Customer

`Transport Job.customer` links directly to ERPNext `Customer`. The custom app does not define a duplicate customer master, and this foundation does not add custom Customer fields.

## Supplier and Transporter

Transporters are modeled as ERPNext `Supplier` records because hired/subcontracted transporters are payable parties and should reuse ERPNext party, contact, address, tax, and payment terms behavior. Every transporter is a supplier, but ordinary suppliers such as fuel, tyre, spare-parts, and workshop suppliers remain valid with `is_transporter = 0`.

ERPNext already provides these standard Supplier fields and they are reused:

- `is_transporter`
- `supplier_type`
- `payment_terms`
- `tax_id`
- `supplier_primary_contact`, `mobile_no`, `email_id`
- `supplier_primary_address`, `primary_address`
- `disabled`

The transport_management app adds only these Supplier custom fields through the idempotent `after_migrate` setup hook:

- `transporter_status`: Active / Inactive
- `default_rate_type`: Per Trip / Per Ton / Per Route

## Own vs Hired Trips

`Transport Trip.execution_source` identifies how a trip is executed:

- `OWN`: requires `vehicle` and `driver`; `transporter` is not required.
- `HIRED`: requires `transporter` and `hired_vehicle`; `hired_driver` is optional for now.

For hired trips, `transporter` links to ERPNext `Supplier`. The selected Supplier must have `is_transporter = 1`, `transporter_status = Active`, and `disabled = 0`.

## Intentionally Deferred

This foundation intentionally does not implement rates, settlements, Purchase Invoice automation, or accounting automation. `default_rate_type` is only a master-data hint for future commercial workflows.

