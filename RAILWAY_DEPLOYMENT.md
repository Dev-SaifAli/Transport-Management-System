# Railway Deployment Preparation

This repository is prepared for a Railway deployment of Frappe v16, ERPNext v16, and the `transport_management` app. Do not deploy production from the development bench directory directly.

## A. Existing Infrastructure Found

- Bench site: `tms.localhost`
- Installed apps in the active site: `frappe`, `erpnext`, `transport_management`
- `sites/apps.txt` also contains an old `vsd_fleet_ms` entry, but `tms.localhost/site_config.json` does not install it. Do not include it in production unless deliberately reintroduced.
- Current versions:
  - Frappe: `version-16`, commit `988e54f3c4c291e2077a83809663f123731abe76`
  - ERPNext: `version-16`, commit `4048fb70e14d1843956fcdabb7c3cca75a1cbcdd`
  - transport_management: `develop`, commit `95d97af9b5193f02f379fb2543e7cd0f711a72e1`
- Existing deployment files: development `Procfile` only.
- No existing Dockerfile, docker-compose file, Railway config, or production env template was found.
- Current `sites/common_site_config.json` is development oriented: `developer_mode`, `live_reload`, fixed local ports, and service names like `mariadb`, `redis-cache`, `redis-queue`.

## B. Docker Approach

Use one custom image for all Railway app services. The image:

- starts from the Frappe bench image,
- initializes a clean bench,
- fetches pinned Frappe and ERPNext refs,
- copies this `transport_management` source into the image,
- runs `bench build --production`,
- ships Railway bootstrap/migration/entrypoint scripts.

Build-time args:

```text
FRAPPE_REF=988e54f3c4c291e2077a83809663f123731abe76
ERPNEXT_REF=4048fb70e14d1843956fcdabb7c3cca75a1cbcdd
FRAPPE_BRANCH=version-16
ERPNEXT_BRANCH=version-16
```

Do not run migrations during Docker build. Railway private database/Redis networking is only available at runtime.

## C. Railway Services

Create separate Railway services:

- `web`
- `websocket`
- `scheduler`
- `worker-default`
- `worker-short`
- `worker-long`
- `mariadb`
- `redis-cache`
- `redis-queue`

All six application services use the same Docker image built from this repository.

## D. Start Commands

Do not use `bench start` in production.

Recommended Railway start commands:

```bash
# web
gunicorn --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} frappe.app:application --preload

# websocket
bash -lc 'export FRAPPE_SOCKETIO_PORT="${PORT:-9000}"; bench socketio'

# scheduler
bench schedule

# worker-default
bench worker --queue default

# worker-short
bench worker --queue short

# worker-long
bench worker --queue long
```

The Docker entrypoint writes runtime Frappe config from env before executing each command.

## E. Required Environment Variables

Use Railway secrets, not committed values.

```text
FRAPPE_SITE
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
REDIS_CACHE_URL
REDIS_QUEUE_URL
REDIS_SOCKETIO_URL
SOCKETIO_URL
```

First bootstrap only:

```text
ADMIN_PASSWORD
DB_ROOT_USER
DB_ROOT_PASSWORD
```

Suggested Railway private hosts:

```text
DB_HOST=mariadb.railway.internal
REDIS_CACHE_URL=redis://redis-cache.railway.internal:6379
REDIS_QUEUE_URL=redis://redis-queue.railway.internal:6379
REDIS_SOCKETIO_URL=redis://redis-queue.railway.internal:6379
```

## F. MariaDB Configuration

MariaDB must be its own Railway service with persistent storage. Do not store database files in the application container.

Expected settings:

- Port: `3306`
- Character set: `utf8mb4`
- Collation: `utf8mb4_unicode_ci`
- Private networking only; do not expose publicly.

Use `DB_ROOT_PASSWORD` only for initial site/database creation if Railway grants root/admin access. If the database and user are pre-created, set `SETUP_DB=0` and provide `DB_NAME`, `DB_USER`, and `DB_PASSWORD`.

## G. Redis Configuration

Use two logical Redis services:

- `redis-cache`
- `redis-queue`

Frappe v16 still reads `redis_socketio`; configure it to the queue Redis unless a separate realtime Redis service is intentionally added:

```text
REDIS_SOCKETIO_URL=${REDIS_QUEUE_URL}
```

Do not expose Redis publicly.

## H. Persistent Volume Strategy

Mount one shared Railway volume at:

```text
/home/frappe/frappe-bench/sites
```

This path must persist and be consistent for web, websocket, scheduler, and workers because it contains:

- `common_site_config.json`
- site `site_config.json`
- public files
- private files
- generated assets under `sites/assets`

The image contains a template copy of the built `sites` directory. On first container startup, the entrypoint seeds the mounted sites volume if it is empty.

## I. First Deployment / Bootstrap

After MariaDB and Redis are reachable and the shared sites volume is attached, run the bootstrap script once:

```bash
/home/frappe/frappe-bench/railway-bootstrap.sh
```

It will:

- wait for MariaDB,
- wait for Redis cache and queue,
- create the site only if `sites/${FRAPPE_SITE}/site_config.json` does not exist,
- install `erpnext` and `transport_management`,
- write DB/Redis site config,
- run `transport_management.setup.after_migrate`,
- clear cache.

It will not recreate an existing site.

## J. Migration / Update Flow

For updates after a new image is deployed, run:

```bash
/home/frappe/frappe-bench/railway-migrate.sh
```

The script runs:

- `bench --site ${FRAPPE_SITE} migrate`
- `bench --site ${FRAPPE_SITE} execute transport_management.setup.after_migrate`
- `bench --site ${FRAPPE_SITE} clear-cache`

The migrate command is wrapped with `RAILWAY_MIGRATE_TIMEOUT_SECONDS` to avoid silent production hangs.

Known development risk: `bench --site tms.localhost migrate` may stall near:

```text
Removing orphan doctypes...
Command: Sleep
```

If this reproduces in Railway, do not keep retrying indefinitely. Inspect logs and database process state, then run targeted `reload-doc` and setup helpers only after confirming schema consistency.

## K. Health Check

Recommended Railway healthcheck path for the `web` service:

```text
/api/method/ping
```

This uses existing Frappe behavior and should return 2xx when the web process is healthy.

## L. Port Handling

Railway injects `PORT` for public services.

- Web binds gunicorn to `${PORT:-8000}`.
- Websocket should export `FRAPPE_SOCKETIO_PORT=${PORT:-9000}` before `bench socketio`.
- Workers and scheduler do not need public ports.

## M. Custom Domain Later

After the web service is stable:

1. Add the custom domain in Railway.
2. Point DNS as Railway instructs.
3. Set `FRAPPE_SITE` to the production hostname.
4. Configure `SOCKETIO_URL` to the public websocket service URL or domain.
5. Clear cache and restart services.

## N. Backup / Restore Preparation

To migrate the current development site later, prepare a complete backup locally:

```bash
bench --site tms.localhost backup --with-files
```

Capture:

- database SQL backup,
- public files archive,
- private files archive,
- `site_config.json` values that are safe to reproduce as Railway secrets.

Restore into Railway only after the target site exists and services are stopped or in maintenance:

```bash
bench --site ${FRAPPE_SITE} restore /path/to/database.sql.gz \
  --with-public-files /path/to/public-files.tar \
  --with-private-files /path/to/private-files.tar
bench --site ${FRAPPE_SITE} migrate
bench --site ${FRAPPE_SITE} clear-cache
```

Do not commit backups, credentials, encryption keys, or Railway URLs with secrets.
