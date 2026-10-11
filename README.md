# AL RANA ERP + TMS Monorepo

This repository contains the AL RANA custom Frappe applications used with
Frappe v16 and ERPNext v16.

## Applications

- `apps/transport_management` - AL RANA Transport Management System.
- `apps/dispatch_portal` - AL RANA Dispatch Console. This app depends on
  `transport_management` and does not duplicate TMS DocTypes or business logic.

Both applications remain independent Frappe apps and can be installed by Bench
from their own folders.

## Docker Deployment

The root `Dockerfile` builds a Bench image with pinned Frappe, ERPNext, HRMS
source availability, and both custom apps from this repository:

1. `frappe`
2. `erpnext`
3. `hrms` available in the image only
4. `transport_management`
5. `dispatch_portal`

HRMS is intentionally not auto-installed by Railway startup scripts. Existing
production sites should be restored first, then migrated or extended with
additional apps only through explicit controlled commands.

## Railway Scripts

- `scripts/railway-entrypoint.sh` prepares runtime config and synchronizes image
  apps/assets into the persistent Bench volume.
- `scripts/railway-bootstrap.sh` is for explicit first-site creation only.
- `scripts/railway-migrate.sh` is an explicit migration helper; migrations do
  not run automatically on normal application startup.

Do not commit backups, site files, secrets, database dumps, uploaded documents,
or Railway volume contents.
