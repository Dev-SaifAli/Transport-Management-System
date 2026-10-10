# syntax=docker/dockerfile:1

ARG BENCH_IMAGE=frappe/bench:latest

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

COPY --chown=frappe:frappe apps/transport_management apps/transport_management
COPY --chown=frappe:frappe apps/dispatch_portal apps/dispatch_portal

RUN ./env/bin/python -m pip install --quiet --upgrade -e apps/transport_management \
    && ./env/bin/python -m pip install --quiet --upgrade -e apps/dispatch_portal \
    && ./env/bin/python -c 'from pathlib import Path; p=Path("sites/apps.txt"); apps=[line.strip() for line in p.read_text().splitlines() if line.strip()]; [apps.append(app) for app in ("transport_management", "dispatch_portal") if app not in apps]; p.write_text("\n".join(apps) + "\n")' \
    && bench build --production

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
    scripts/railway-clear-asset-cache.py \
    /home/frappe/frappe-bench/railway-clear-asset-cache.py

RUN chmod +x \
    /home/frappe/frappe-bench/railway-entrypoint.sh \
    /home/frappe/frappe-bench/railway-bootstrap.sh \
    /home/frappe/frappe-bench/railway-migrate.sh \
    /home/frappe/frappe-bench/railway-clear-asset-cache.py \
    /home/frappe/frappe-bench/railway-install-hrms.sh

USER frappe
WORKDIR /home/frappe/frappe-bench

ENV FRAPPE_BENCH_ROOT=/home/frappe/frappe-bench \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/home/frappe/frappe-bench/railway-entrypoint.sh"]

CMD ["bash", "-lc", "cd /home/frappe/frappe-bench/sites && exec /home/frappe/frappe-bench/env/bin/gunicorn --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} transport_management.railway_wsgi:application --preload"]
