import { apiMock } from '@/config'
import { mockDispatchBoard } from '@/mock/dispatchBoard'
import type { DispatchBoardData } from '@/types/board'

import { httpClient } from './client'

/** Feature service contract — components depend only on this interface. */
export interface DispatchBoardService {
  getBoard(): Promise<DispatchBoardData>
}

const mockDispatchBoardService: DispatchBoardService = {
  async getBoard(): Promise<DispatchBoardData> {
    await new Promise((resolve) => setTimeout(resolve, 250))
    return structuredClone(mockDispatchBoard)
  },
}

/**
 * Frappe-backed implementation — swap in when API contracts are available:
 *   return frappe.list('Transport Trip', { filters: ... })
 * No component changes needed when this is enabled (VITE_API_MOCK=false).
 */
const frappeDispatchBoardService: DispatchBoardService = {
  async getBoard(): Promise<DispatchBoardData> {
    void httpClient
    throw new Error('Frappe dispatch board API not yet configured. Set VITE_API_MOCK=true.')
  },
}

export function createDispatchBoardService(): DispatchBoardService {
  return apiMock ? mockDispatchBoardService : frappeDispatchBoardService
}