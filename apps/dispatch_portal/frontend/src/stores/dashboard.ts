import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'

import { createDashboardService, type DashboardService } from '@/services/api/dashboard'
import type { DashboardOverview, KpiStat } from '@/types/dashboard'

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

  async function fetchDashboardData(): Promise<void> {
    await fetchOverview()
  }

  async function refresh(): Promise<void> {
    await fetchOverview()
  }

  // Reactive accessors mapped directly from live Frappe backend data
  const kpiMap = computed(() => {
    const map = new Map<string, KpiStat>()
    if (overview.value?.kpis) {
      overview.value.kpis.forEach((k) => map.set(k.id, k))
    }
    return map
  })

  const todaysTrips = computed(() => parseInt(kpiMap.value.get('todays-trips')?.value || '0', 10))
  const unassignedTrips = computed(() => parseInt(kpiMap.value.get('unassigned-trips')?.value || '0', 10))
  const activeNow = computed(() => parseInt(kpiMap.value.get('active-now')?.value || '0', 10))
  const trucksAvailable = computed(() => parseInt(kpiMap.value.get('trucks-available')?.value || '0', 10))
  const scheduled = computed(() => parseInt(kpiMap.value.get('scheduled')?.value || '0', 10))
  const completed = computed(() => parseInt(kpiMap.value.get('completed')?.value || '0', 10))
  const needAttention = computed(() => parseInt(kpiMap.value.get('need-attention')?.value || '0', 10))
  const driversAvailable = computed(() => parseInt(kpiMap.value.get('drivers-available')?.value || '0', 10))

  const todaysDispatch = computed(() => overview.value?.todaysDispatch || [])
  const fleetMarkers = computed(() => overview.value?.fleetMap.markers || [])
  const pendingAssignments = computed(() => overview.value?.pendingAssignments || [])
  const awaitingVerification = computed(() => overview.value?.awaitingVerification || [])
  const recentActivity = computed(() => overview.value?.recentActivity || [])

  return {
    overview,
    status,
    error,
    fetchOverview,
    fetchDashboardData,
    refresh,
    todaysTrips,
    unassignedTrips,
    activeNow,
    trucksAvailable,
    scheduled,
    completed,
    needAttention,
    driversAvailable,
    todaysDispatch,
    fleetMarkers,
    pendingAssignments,
    awaitingVerification,
    recentActivity,
  }
})
