/**
 * Central, environment-driven application configuration.
 *
 * Everything that differs between hosting environments (Frappe subpath
 * embedding, API origin, asset origin) is resolved here from Vite env
 * variables so the source code stays hosting-agnostic.
 *
 * See `.env.example` for the full list of supported variables.
 */

interface ImportMetaEnv {
  readonly VITE_APP_BASE_PATH?: string
  readonly VITE_API_BASE_URL?: string
  readonly VITE_ASSET_BASE_URL?: string
  readonly VITE_API_MOCK?: string
}

function env(): ImportMetaEnv {
  return (import.meta as unknown as { env: ImportMetaEnv }).env ?? {}
}

/** URL path the app is served under (e.g. `/dispatch/`). */
export const appBasePath: string = env().VITE_APP_BASE_PATH ?? '/dispatch/'

/**
 * Base URL the router should use. Relative Vite bases (e.g. `./` used for
 * portable static builds) fall back to `/` because vue-router needs an
 * absolute base.
 */
export const routerBasePath: string = appBasePath.startsWith('.') ? '/' : appBasePath

/** Base URL for API requests (Frappe REST API origin/prefix). */
export const apiBaseUrl: string = env().VITE_API_BASE_URL ?? '/api'

/** Base path for runtime-resolved static assets. Empty = relative to app base. */
export const assetBaseUrl: string = env().VITE_ASSET_BASE_URL ?? ''

/** When true, services return local mock data instead of calling Frappe. */
export const apiMock: boolean = (env().VITE_API_MOCK ?? 'false') === 'true'

/** Resolve an asset path against the configured asset base. */
export function assetUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${assetBaseUrl}${normalized}`
}
