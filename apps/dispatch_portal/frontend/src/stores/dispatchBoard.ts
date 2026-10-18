import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'

import {
  createDispatchBoardService,
  type DispatchBoardService,
} from '@/services/api/dispatchBoard'
import type { BoardColumnKey, DispatchBoardData } from '@/types/board'

import type { LoadStatus } from './dashboard'

export const useDispatchBoardStore = defineStore('dispatchBoard', () => {
  const service: DispatchBoardService = createDispatchBoardService()

  const data = shallowRef<DispatchBoardData | null>(null)
  const status = ref<LoadStatus>('idle')
  const error = ref<string | null>(null)

  async function fetchBoard(): Promise<void> {
    if (status.value === 'loading') return
    status.value = 'loading'
    error.value = null
    try {
      data.value = await service.getBoard()
      status.value = 'success'
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load dispatch board.'
      status.value = 'error'
    }
  }

  const totalTrips = computed(() => data.value?.trips.length ?? 0)
  const columnCount = computed(() => data.value?.columns.length ?? 0)

  function tripsFor(column: BoardColumnKey) {
    return computed(() => data.value?.trips.filter((t) => t.column === column) ?? [])
  }

  return { data, status, error, fetchBoard, totalTrips, columnCount, tripsFor }
})