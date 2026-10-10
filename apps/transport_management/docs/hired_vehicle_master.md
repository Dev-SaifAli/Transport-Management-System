# Hired Vehicle Master

`Hired Vehicle` is a lightweight transport_management DocType for subcontracted trucks supplied by transporter Suppliers. It is separate from TMS `Truck`, which remains the owned-fleet operational master.

## Model

A hired vehicle belongs to one ERPNext `Supplier` where `is_transporter = 1`. The master stores the plate number, optional vehicle type and capacity, optional registration and insurance expiry dates, optional default driver text, and an `active` flag.

Duplicate plate numbers are blocked for the same transporter. The same plate under different transporters is not globally blocked in this phase because cross-company plate data quality and ownership rules need business confirmation.

## Transport Trip

For `execution_source = HIRED`, Transport Trip requires:

- active/enabled transporter Supplier
- active Hired Vehicle belonging to that transporter
- optional hired driver text

Own fleet `vehicle` and `driver` remain required only for `execution_source = OWN`.

## Deferred

This phase does not implement rates, settlement, Purchase Invoice automation, accounting, compliance alerts, expiry reminders, hired driver masters, or dynamic hired vehicle availability.
