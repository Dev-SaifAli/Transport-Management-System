import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'

import { createDashboardService, type DashboardService } from '@/services/api/dashboard'
import type { DashboardOverview } from '@/types/dashboard'

export type LoadStatus = 'idle' | 'loading' | 'success' | 'error'

export const useDashboardStore = defineStore('dashboard', () => {
  const service: DashboardService = createDashboardService()

  const overview = shallowRef<DashboardOverview | null>(null)
  const status = ref<LoadStatus>('idle')
  const error = ref<string | null>(null)

  async function fetchOverview(): Promise<void> {
    if (status.value === 'loading') return
    status.value = 'loading'
    error.value = null
    try {
      overview.value = await service.getOverview()
      status.value = 'success'
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load dashboard data.'
      status.value = 'error'
    }
  }

  async function refresh(): Promise<void> {
    await fetchOverview()
  }

  return { overview, status, error, fetchOverview, refresh }
})
