# Transport Trip Phase 1

The standalone TMS production flow is:

Transport Job -> 1..N Transport Trips -> execution/POD -> costs, settlement, and accounting in later phases.

`Transport Trip` is the production execution entity owned by transport_management. It intentionally does not use Fleet `Trips` or `Manifest` because those Fleet DocTypes are coupled to the legacy Manifest/Cargo Registration/fuel/fund flow.

Fleet-origin masters that are now owned by `transport_management` are reused where they are clean masters: `Truck`, `Truck Driver`, `Transport Location`, `Cargo Types`, and ERPNext `UOM`.

Fuel, toll, expenses, settlement, accounting, Fleet Trips adapters, Manifest integration, and Transportation Order compatibility are not implemented in the active TMS workflow.
