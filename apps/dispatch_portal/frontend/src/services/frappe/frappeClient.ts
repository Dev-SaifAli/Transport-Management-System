import { httpClient } from '@/services/api/client'

/**
 * Thin Frappe REST helpers.
 *
 * The Frappe framework exposes:
 *  - CRUD on DocTypes:  GET/POST /api/resource/:doctype, /api/resource/:doctype/:name
 *  - Whitelisted methods: /api/method/:dotted.path
 *
 * Authentication is handled centrally by the HTTP client (session cookie or
 * token). No credentials may be stored in this repository.
 */
export const frappe = {
  /** Fetch a list of documents for a DocType, e.g. list('Transport Trip', { filters: ... }). */
  list<T>(doctype: string, params?: Record<string, unknown>): Promise<T> {
    return httpClient.get(`/resource/${doctype}`, { params })
  },

  /** Fetch a single document by name. */
  get<T>(doctype: string, name: string): Promise<T> {
    return httpClient.get(`/resource/${doctype}/${encodeURIComponent(name)}`)
  },

  /** Create a document. */
  create<T>(doctype: string, doc: Record<string, unknown>): Promise<T> {
    return httpClient.post(`/resource/${doctype}`, doc)
  },

  /** Update a document. */
  update<T>(doctype: string, name: string, doc: Record<string, unknown>): Promise<T> {
    return httpClient.put(`/resource/${doctype}/${encodeURIComponent(name)}`, doc)
  },

  /** Call a whitelisted Frappe method, e.g. call('dispatch_portal.api.assign_truck', {...}). */
  call<T>(method: string, args?: Record<string, unknown>): Promise<T> {
    return httpClient.post(`/method/${method}`, args)
  },
}
