# Transport Management

Standalone ERP + Transportation Management System built as a custom Frappe / ERPNext app.

This repository contains only the `transport_management` custom app. It is intended to be installed inside a Frappe bench alongside Frappe and ERPNext, without modifying upstream framework or core app source code.

## Current Scope

The app supports the foundation for own-fleet and hired/subcontracted transport operations.

Current major modules:

- Transport Job
- Transport Trip
- Customer / Supplier / Transporter foundation
- Transport Locations
- Owned Truck master
- Hired Vehicle
- Transport Management workspace

Transporters are modeled as ERPNext Suppliers with transport-specific attributes. Owned fleet uses the TMS-owned Truck master. Hired/subcontracted fleet uses the lightweight Hired Vehicle master.

## Installation

Install from a Frappe bench:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench --site $SITE_NAME install-app transport_management
bench --site $SITE_NAME migrate
```

Replace `$URL_OF_THIS_REPO` and `$SITE_NAME` for your environment.

## Development

Run tests with:

```bash
bench --site tms.localhost run-tests --app transport_management
```

Useful development commands:

```bash
bench --site tms.localhost migrate
bench --site tms.localhost clear-cache
```

This app uses `pre-commit` for local code checks. To enable it:

```bash
cd apps/transport_management
pre-commit install
```

Configured tools include:

- ruff
- eslint
- prettier
- pyupgrade

## Deferred Areas

The current implementation does not include rate management, settlement automation, Purchase Invoice automation, accounting automation, compliance alerts, GPS/geofencing, or route pricing.

## License

MIT
