# Transport Job Phase 1

The standalone TMS production flow is:

Transport Job -> 1..N Transport Trips -> execution, POD, costs, settlement, and accounting in later phases.

`Transport Job` represents one customer transport requirement. It stores the customer, requested date, loading and unloading sites, material, requested quantity, UOM, business references, special instructions, and status.

Vehicle, driver, GDN, loading number, unloading number, POD, fuel, toll, and execution expenses belong to Trip execution and should not be added here.

`Transport Shipment` is deprecated and kept only for the earlier working demo. Do not add new production behavior to it. Existing records must remain intact.

Fleet `Transportation Order` is also kept for compatibility and old demo data. The `assign_transport` compatibility shim remains because Fleet's controller and client script still expect that child table.
