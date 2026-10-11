# Transport Job Phase 1

The standalone TMS production flow is:

Transport Job -> 1..N Transport Trips -> execution, POD, costs, settlement, and accounting in later phases.

`Transport Job` represents one customer transport requirement. It stores the customer, requested date, loading and unloading sites, material, requested quantity, UOM, business references, special instructions, and status.

Vehicle, driver, GDN, loading number, unloading number, POD, fuel, toll, and execution expenses belong to Trip execution and should not be added here.

`Transport Shipment` is retired and kept only for historical readability from the earlier working demo. Its old Fleet references are plain text, not active Link dependencies. Do not add new production behavior to it. Existing records must remain intact.

Fleet `Transportation Order` compatibility is retired from the active TMS product. Existing Fleet records are left untouched, but new TMS work should use Transport Job and Transport Trip.
