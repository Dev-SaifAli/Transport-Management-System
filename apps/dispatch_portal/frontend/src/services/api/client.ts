import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios'

import { apiBaseUrl } from '@/config'

/**
 * Normalized API error, decoupling components from Axios/Frappe specifics.
 */
export class ApiError extends Error {
  readonly status?: number
  readonly code?: string

  constructor(message: string, status?: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export interface HttpClient {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T>
}

/**
 * Central Axios instance.
 *
 * - `baseURL` comes from configuration (never hardcoded).
 * - `withCredentials` enables Frappe session-cookie authentication when the
 *   portal is served from the same Frappe site. If token auth is used
 *   instead, attach the Authorization header in the interceptor below —
 *   load the token from configuration or the hosting environment, never
 *   from source code.
 */
const instance: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  headers: { Accept: 'application/json' },
  // Frappe rejects cross-site requests without CSRF handling; when the app
  // is embedded on the Frappe origin, cookies + the X-Frappe-CSRF-Token
  // header (read from the `csrf_token` cookie by Frappe's own JS) apply.
})

instance.interceptors.request.use((config) => {
  const csrfToken = readCookie('csrf_token')
  if (csrfToken && !isSafeMethod(config.method)) {
    config.headers.set('X-Frappe-CSRF-Token', csrfToken)
  }
  return config
})

instance.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Frappe returns errors as { exc_type, exception, _server_messages }.
    const data = error.response?.data as { exception?: string; message?: string } | undefined
    return Promise.reject(
      new ApiError(
        data?.message ?? data?.exception ?? error.message,
        error.response?.status,
        error.code,
      ),
    )
  },
)

function isSafeMethod(method?: string): boolean {
  return method === 'get' || method === 'head' || method === 'options'
}

function readCookie(name: string): string | undefined {
  if (typeof document === 'undefined') return undefined
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match?.[1]
}

export const httpClient: HttpClient = {
  get: (url, config) => instance.get(url, config).then((r) => r.data as never),
  post: (url, data, config) => instance.post(url, data, config).then((r) => r.data as never),
  put: (url, data, config) => instance.put(url, data, config).then((r) => r.data as never),
  delete: (url, config) => instance.delete(url, config).then((r) => r.data as never),
}
