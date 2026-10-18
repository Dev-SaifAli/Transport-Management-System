import { apiMock } from '@/config'
import { mockDashboardOverview } from '@/mock/dashboard'
import type { DashboardOverview } from '@/types/dashboard'

import { httpClient } from './client'

/**
 * Feature service contract. Components and stores only depend on this
 * interface — the data source (mock vs Frappe) is an implementation detail.
 */
export interface DashboardService {
  getOverview(): Promise<DashboardOverview>
}

/**
 * Mock implementation backed by local sample data.
 * Used while `VITE_API_MOCK=true`.
 */
const mockDashboardService: DashboardService = {
  async getOverview(): Promise<DashboardOverview> {
    // Simulated network latency keeps loading states honest during UI review.
    await new Promise((resolve) => setTimeout(resolve, 250))
    return structuredClone(mockDashboardOverview)
  },
}

/**
 * Frappe-backed implementation.
 *
 * NOTE: endpoint paths and response shapes must be finalized once the Frappe
 * `dispatch_portal` API contracts are available. This skeleton exists so the
 * swap is a one-line change (VITE_API_MOCK=false) with no component edits.
 */
const frappeDashboardService: DashboardService = {
  async getOverview(): Promise<DashboardOverview> {
    // TODO(dispatch_portal-api): replace with the real endpoint, e.g.
    //   return httpClient.get<DashboardOverview>('/resource/Transport Trip?...')
    // or a dedicated whitelisted method: /api/method/dispatch_portal.api.dashboard
    void httpClient
    throw new Error('Frappe dashboard API not yet configured. Set VITE_API_MOCK=true.')
  },
}

export function createDashboardService(): DashboardService {
  return apiMock ? mockDashboardService : frappeDashboardService
}
