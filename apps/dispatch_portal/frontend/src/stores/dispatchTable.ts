import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'

import {
  createDispatchTableService,
  type DispatchTableService,
} from '@/services/api/dispatchTable'
import type { DispatchTableData, DispatchTableTrip } from '@/types/dispatchTable'

import type { LoadStatus } from './dashboard'

export type SortKey = 'id' | 'window'
export type SortDir = 'asc' | 'desc'

/** Extracts "06:00" from "Today 06:00" for chronological sorting. */
function windowMinutes(label: string): number {
  const match = label.match(/(\d{2}):(\d{2})/)
  return match ? Number(match[1]) * 60 + Number(match[2]) : 0
}

export const useDispatchTableStore = defineStore('dispatchTable', () => {
  const service: DispatchTableService = createDispatchTableService()

  const data = shallowRef<DispatchTableData | null>(null)
  const status = ref<LoadStatus>('idle')
  const error = ref<string | null>(null)

  const search = ref('')
  const activeFilters = ref<{ label: string }[]>([])
  const selectedIds = ref<Set<string>>(new Set())

  const sortKey = ref<SortKey>('window')
  const sortDir = ref<SortDir>('asc')

  async function fetchTrips(): Promise<void> {
    if (status.value === 'loading') return
    status.value = 'loading'
    error.value = null
    try {
      data.value = await service.getTrips()
      activeFilters.value = [...data.value.activeFilters]
      status.value = 'success'
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load dispatch table.'
      status.value = 'error'
    }
  }

  const visibleTrips = computed<DispatchTableTrip[]>(() => {
    const trips = data.value?.trips ?? []
    const q = search.value.trim().toLowerCase()
    const filtered = q
      ? trips.filter((t) =>
          [t.id, t.customer, t.truck ?? '', t.driver ?? '', t.material, t.route]
            .some((f) => f.toLowerCase().includes(q)),
        )
      : [...trips]

    filtered.sort((a, b) => {
      const dir = sortDir.value === 'asc' ? 1 : -1
      if (sortKey.value === 'id') return a.id.localeCompare(b.id) * dir
      return (windowMinutes(a.window) - windowMinutes(b.window)) * dir
    })
    return filtered
  })

  const visibleIds = computed(() => visibleTrips.value.map((t) => t.id))

  const allVisibleSelected = computed(
    () => visibleIds.value.length > 0 && visibleIds.value.every((id) => selectedIds.value.has(id)),
  )

  function toggleSort(key: SortKey): void {
    if (sortKey.value === key) {
      sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortKey.value = key
      sortDir.value = 'asc'
    }
  }

  function toggleTrip(id: string): void {
    const next = new Set(selectedIds.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    selectedIds.value = next
  }

  function toggleAllVisible(): void {
    const next = new Set(selectedIds.value)
    if (allVisibleSelected.value) {
      visibleIds.value.forEach((id) => next.delete(id))
    } else {
      visibleIds.value.forEach((id) => next.add(id))
    }
    selectedIds.value = next
  }

  function clearSelection(): void {
    selectedIds.value = new Set()
  }

  function removeFilter(label: string): void {
    activeFilters.value = activeFilters.value.filter((f) => f.label !== label)
  }

  function clearFilters(): void {
    activeFilters.value = []
  }

  const selectedTrips = computed(() =>
    (data.value?.trips ?? []).filter((t) => selectedIds.value.has(t.id)),
  )

  return {
    data, status, error, fetchTrips,
    search, activeFilters, selectedIds,
    sortKey, sortDir, visibleTrips, allVisibleSelected,
    toggleSort, toggleTrip, toggleAllVisible, clearSelection,
    removeFilter, clearFilters, selectedTrips,
  }
})