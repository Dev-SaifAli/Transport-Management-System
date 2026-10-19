# syntax=docker/dockerfile:1

ARG BENCH_IMAGE=frappe/bench:latest

# Build the nested Vue app explicitly; bench build only packages Frappe assets.
FROM node:24.21.0-bookworm-slim AS dispatch-frontend

WORKDIR /build/apps/dispatch_portal/frontend
RUN npm install --global pnpm@12.11.2
COPY apps/dispatch_portal/frontend/package.json apps/dispatch_portal/frontend/pnpm-lock.yaml apps/dispatch_portal/frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/dispatch_portal/frontend/ ./
RUN VITE_API_MOCK=false VITE_API_BASE_URL=/api VITE_APP_BASE_PATH=/dispatch/ VITE_ASSET_BASE_URL= pnpm run build

FROM ${BENCH_IMAGE} AS builder

ARG FRAPPE_REPO=https://github.com/frappe/frappe.git
ARG FRAPPE_BRANCH=version-16
ARG FRAPPE_REF=988e54f3c4c291e2077a83809663f123731abe76

ARG ERPNEXT_REPO=https://github.com/frappe/erpnext.git
ARG ERPNEXT_BRANCH=version-16
ARG ERPNEXT_REF=4048fb70e14d1843956fcdabb7c3cca75a1cbcdd

ARG HRMS_REPO=https://github.com/frappe/hrms.git
ARG HRMS_BRANCH=version-16
ARG HRMS_REF=6f5ac249283f6fa1013fd5616f3d95f686ba7bb2

USER frappe
WORKDIR /home/frappe

RUN bench init \
    --skip-redis-config-generation \
    --frappe-path "${FRAPPE_REPO}" \
    --frappe-branch "${FRAPPE_BRANCH}" \
    frappe-bench \
    && cd frappe-bench/apps/frappe \
    && git fetch --depth 1 "${FRAPPE_REPO}" "${FRAPPE_REF}" \
    && git checkout --detach FETCH_HEAD

WORKDIR /home/frappe/frappe-bench

RUN bench get-app \
        --branch "${ERPNEXT_BRANCH}" \
        "${ERPNEXT_REPO}" \
    && cd apps/erpnext \
    && git fetch --depth 1 "${ERPNEXT_REPO}" "${ERPNEXT_REF}" \
    && git checkout --detach FETCH_HEAD

RUN bench get-app \
        --branch "${HRMS_BRANCH}" \
        "${HRMS_REPO}" \
    && cd apps/hrms \
    && git fetch --depth 1 "${HRMS_REPO}" "${HRMS_REF}" \
    && git checkout --detach FETCH_HEAD

# The pinned upstream HRMS commit contains a patch that references the legacy
# `Repost Accounting Ledger Settings` DocType, removed in Frappe/ERPNext v16.
# Overlay the reviewed compatibility fix so the pin stays reproducible.
COPY --chown=frappe:frappe \
    patches/hrms/v14_0/add_expense_claim_to_repost_settings.py \
    apps/hrms/hrms/patches/v14_0/add_expense_claim_to_repost_settings.py

COPY --chown=frappe:frappe apps/transport_management apps/transport_management
COPY --chown=frappe:frappe apps/dispatch_portal apps/dispatch_portal

# Copy build output directly from the Node stage, including Git-ignored assets.
COPY --from=dispatch-frontend --chown=frappe:frappe \
    /build/apps/dispatch_portal/dispatch_portal/public/frontend \
    apps/dispatch_portal/dispatch_portal/public/frontend
COPY --from=dispatch-frontend --chown=frappe:frappe \
    /build/apps/dispatch_portal/dispatch_portal/www/dispatch.html \
    apps/dispatch_portal/dispatch_portal/www/dispatch.html

RUN ./env/bin/python -m pip install --quiet --upgrade -e apps/transport_management \
    && ./env/bin/python -m pip install --quiet --upgrade -e apps/dispatch_portal \
    && ./env/bin/python -c 'from pathlib import Path; p=Path("sites/apps.txt"); apps=[line.strip() for line in p.read_text().splitlines() if line.strip()]; [apps.append(app) for app in ("transport_management", "dispatch_portal") if app not in apps]; p.write_text("\n".join(apps) + "\n")' \
    && bench build --production \
    && node apps/dispatch_portal/frontend/scripts/verify-build.mjs

FROM ${BENCH_IMAGE} AS runtime

USER root

COPY --from=builder --chown=frappe:frappe \
    /home/frappe/frappe-bench \
    /home/frappe/frappe-bench

RUN mkdir -p \
        /opt/frappe \
        /home/frappe/logs \
        /home/frappe/frappe-bench/logs \
    && cp -a /home/frappe/frappe-bench/sites /opt/frappe/sites-template \
    && chown -R frappe:frappe \
        /opt/frappe \
        /home/frappe/logs \
        /home/frappe/frappe-bench

COPY --chown=frappe:frappe \
    scripts/railway-entrypoint.sh \
    /home/frappe/frappe-bench/railway-entrypoint.sh

COPY --chown=frappe:frappe \
    scripts/railway-bootstrap.sh \
    /home/frappe/frappe-bench/railway-bootstrap.sh

COPY --chown=frappe:frappe \
    scripts/railway-install-hrms.sh \
    /home/frappe/frappe-bench/railway-install-hrms.sh

COPY --chown=frappe:frappe \
    scripts/railway-migrate.sh \
    /home/frappe/frappe-bench/railway-migrate.sh

COPY --chown=frappe:frappe \
    scripts/railway-start-all.sh \
    /home/frappe/frappe-bench/railway-start-all.sh

COPY --chown=frappe:frappe \
    scripts/railway-clear-asset-cache.py \
    /home/frappe/frappe-bench/railway-clear-asset-cache.py

RUN chmod +x \
    /home/frappe/frappe-bench/railway-entrypoint.sh \
    /home/frappe/frappe-bench/railway-bootstrap.sh \
    /home/frappe/frappe-bench/railway-migrate.sh \
    /home/frappe/frappe-bench/railway-start-all.sh \
    /home/frappe/frappe-bench/railway-clear-asset-cache.py \
    /home/frappe/frappe-bench/railway-install-hrms.sh

# The base image's bench shim runs under a Python that has neither the `bench`
# package nor its dependencies (`click`), so `bench`, `bench schedule` and
# `bench worker` all fail. The bench virtualenv has both, so point the shim at
# it and put the bench package on the path.
ENV PYTHONPATH=/home/frappe/.bench

RUN printf '#!/usr/bin/env bash\nexec /home/frappe/frappe-bench/env/bin/python -c "from bench.cli import cli; cli()" "$@"\n' \
        > /home/frappe/.local/bin/bench \
    && chmod +x /home/frappe/.local/bin/bench \
    && chown frappe:frappe /home/frappe/.local/bin/bench

USER root
WORKDIR /home/frappe/frappe-bench

ENV FRAPPE_BENCH_ROOT=/home/frappe/frappe-bench \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/home/frappe/frappe-bench/railway-entrypoint.sh"]

CMD ["bash", "-lc", "/home/frappe/frappe-bench/railway-start-all.sh"]
