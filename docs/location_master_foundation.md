# Location Master Foundation

## Transport Location

The standalone TMS reuses the existing `Transport Location` DocType supplied by `vsd_fleet_ms`. The transport_management app does not edit Fleet source files and does not create a duplicate location master.

Fleet already provides:

- `location`
- `country`

The transport_management app extends `Transport Location` through idempotent custom fields installed from `after_migrate`:

- `location_type`: Customer Site / Supplier Site / Plant / Yard / Warehouse / Port / Other
- `customer`: optional link to ERPNext Customer
- `supplier`: optional link to ERPNext Supplier
- `address`: optional link to ERPNext Address
- `city`
- `latitude`
- `longitude`
- `active`: default 1
- `notes`

## Operational Site Ownership

Customer and Supplier links are optional. Normally, an operational site should belong to the relevant party type: customer sites link to Customer, supplier/transporter sites link to Supplier. This phase does not enforce complex ownership rules because yards, warehouses, plants, and ports may be internal or shared operational sites.

Use ERPNext Address for full address details. Transport Location keeps only lightweight operational attributes and an optional Address link.

## Job and Trip Behavior

`Transport Job.loading_site` and `Transport Job.unloading_site` link to `Transport Location`.

`Transport Trip.loading_site` and `Transport Trip.unloading_site` also link to `Transport Location`; defaults are copied from the Transport Job when creating a trip.

Server-side validation rejects same loading/unloading locations and inactive Transport Locations. Client-side filters hide inactive locations where practical, but server validation remains authoritative.

## Route Master Decision

No dedicated Route DocType is introduced in this phase. The TMS currently needs origin and destination only. A route/lane master should be introduced later only when reusable lane data is required, such as distance, expected duration, toll estimates, fixed route costs, or route-specific rate references.

Fleet `Trip Routes` is intentionally not used because it carries Fleet-specific route steps, fuel consumption, and fixed expense behavior that is not part of this standalone TMS phase.

## Deferred

This phase does not implement route masters, distance calculations, route pricing, toll estimation, GPS/geofencing, or rate management.
