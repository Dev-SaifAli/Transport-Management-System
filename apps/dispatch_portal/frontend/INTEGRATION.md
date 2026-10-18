# Embedding the Dispatch Portal into Frappe (`dispatch_portal`)

The Vue source is hosting-agnostic. Nothing in `src/` references localhost,
external domains, or credentials. Integration only requires build-time
configuration plus serving the static build from the Frappe app.

## 1. Build

```bash
cp .env.example .env
# defaults are already correct for a subpath deployment:
#   VITE_APP_BASE_PATH=/dispatch/
pnpm install
pnpm build        # outputs to dist/
```

## 2. Serve from the Frappe app

Copy the contents of `dist/` into the `dispatch_portal` app's `public/dispatch`
folder (Frappe serves `public/` at the site root, so the app is available at
`/dispatch/`). Because the build uses a relative asset base, it also works from
the domain root or any other subpath without rebuilding.

In Frappe, add `/dispatch` to the guest-allowed or role-controlled page access
as appropriate for your permission model.

## 3. API and authentication

- `VITE_API_BASE_URL` (default `/api`) is the Frappe REST prefix. When the
  portal is served from the same Frappe origin, session cookies authenticate
  requests automatically (`withCredentials` is enabled).
- Write requests send the `X-Frappe-CSRF-Token` header read from Frappe's
  `csrf_token` cookie (handled in `src/services/api/client.ts`).
- If you use token auth instead, attach the `Authorization` header in the same
  interceptor — load the token from configuration/environment, never from
  source code.

## 4. Switching from mock data to Frappe APIs

1. Implement the service interface in
   `src/services/api/dashboard.ts` (`frappeDashboardService`) using the
   helpers in `src/services/frappe/frappeClient.ts`
   (`frappe.list`, `frappe.get`, `frappe.call`, …).
2. Set `VITE_API_MOCK=false` and rebuild.

Components, stores, and routes do not change — they depend only on the
`DashboardService` interface and shared types in `src/types/`.
