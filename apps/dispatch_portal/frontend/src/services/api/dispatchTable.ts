import { apiMock } from '@/config'
import { mockDispatchTable } from '@/mock/dispatchTable'
import type { DispatchTableData } from '@/types/dispatchTable'

import { httpClient } from './client'

/** Feature service contract — components depend only on this interface. */
export interface DispatchTableService {
  getTrips(): Promise<DispatchTableData>
}

const mockDispatchTableService: DispatchTableService = {
  async getTrips(): Promise<DispatchTableData> {
    await new Promise((resolve) => setTimeout(resolve, 250))
    return structuredClone(mockDispatchTable)
  },
}

/**
 * Frappe-backed implementation — swap in when API contracts are available:
 *   return frappe.list('Transport Trip', { filters: ... })
 */
const frappeDispatchTableService: DispatchTableService = {
  async getTrips(): Promise<DispatchTableData> {
    void httpClient
    throw new Error('Frappe dispatch table API not yet configured. Set VITE_API_MOCK=true.')
  },
}

export function createDispatchTableService(): DispatchTableService {
  return apiMock ? mockDispatchTableService : frappeDispatchTableService
}