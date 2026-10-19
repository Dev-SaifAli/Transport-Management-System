import { refDebounced } from '@vueuse/core'
import { defineStore } from 'pinia'
import { computed, ref, shallowRef, watch } from 'vue'
import { createQuotationsService, type QuotationsService } from '@/services/api/quotations'
import type { QuotationTabKey, TransportQuotation } from '@/types/quotations'
import type { LoadStatus } from './dashboard'

export type QuotationSortKey = 'id' | 'date'
export type DateFilter = 'all' | 'quarter' | 'month'

function toTime(label: string): number {
  return new Date(label.replace(/(\d{2}) (\w{3}) (\d{4})/, '$2 $1, $3')).getTime()
}

export const useQuotationsStore = defineStore('quotations', () => {
  const service: QuotationsService = createQuotationsService()

  const tabs = shallowRef<{ key: QuotationTabKey; label: string; count: number }[]>([])
  const rows = shallowRef<TransportQuotation[]>([])
  const status = ref<LoadStatus>('idle')
  const error = ref<string | null>(null)

  const search = ref('')
  const debouncedSearch = refDebounced(search, 300)

  const activeTab = ref<QuotationTabKey>('all')
  const customerFilter = ref<string>('all')
  const statusFilter = ref<'all' | TransportQuotation['status']>('all')
  const dateFilter = ref<DateFilter>('all')

  const sortKey = ref<QuotationSortKey>('id')
  const sortDir = ref<'asc' | 'desc'>('asc')
  const pageIndex = ref(0)
  const pageSize = ref(10)

  async function fetchQuotations(): Promise<void> {
    if (status.value === 'loading') return
    status.value = 'loading'
    error.value = null
    try {
      const data = await service.getQuotations()
      tabs.value = data.tabs
      rows.value = data.rows
      status.value = 'success'
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load quotations.'
      status.value = 'error'
    }
  }

  const customers = computed(() => [...new Set(rows.value.map((r) => r.customer))].sort())
  const referenceDate = computed(() => Math.max(...rows.value.map((r) => toTime(r.quotationDate)), 0))

  const filteredRows = computed<TransportQuotation[]>(() => {
    const q = debouncedSearch.value.trim().toLowerCase()
    const refDate = new Date(referenceDate.value)
    const quarter = Math.floor(refDate.getMonth() / 3)

    let result = rows.value.filter((row) => {
      if (activeTab.value !== 'all' && row.status !== activeTab.value) return false
      if (customerFilter.value !== 'all' && row.customer !== customerFilter.value) return false
      if (statusFilter.value !== 'all' && row.status !== statusFilter.value) return false
      if (dateFilter.value !== 'all') {
        const d = new Date(toTime(row.quotationDate))
        if (dateFilter.value === 'quarter' && !(d.getFullYear() === refDate.getFullYear() && Math.floor(d.getMonth() / 3) === quarter)) return false
        if (dateFilter.value === 'month' && !(d.getFullYear() === refDate.getFullYear() && d.getMonth() === refDate.getMonth())) return false
      }
      if (q && ![row.id, row.customer, row.materials, row.createdBy].some((f) => f.toLowerCase().includes(q))) return false
      return true
    })

    result = [...result].sort((a, b) => {
      const dir = sortDir.value === 'asc' ? 1 : -1
      const av = sortKey.value === 'id' ? a.id : toTime(a.quotationDate)
      const bv = sortKey.value === 'id' ? b.id : toTime(b.quotationDate)
      return av > bv ? dir : av < bv ? -dir : 0
    })
    return result
  })

  const totalFiltered = computed(() => filteredRows.value.length)
  const pageCount = computed(() => Math.max(Math.ceil(totalFiltered.value / pageSize.value), 1))

  const pageRows = computed<TransportQuotation[]>(() => {
    const start = pageIndex.value * pageSize.value
    return filteredRows.value.slice(start, start + pageSize.value)
  })

  const activePills = computed<{ key: string; label: string }[]>(() => {
    const pills: { key: string; label: string }[] = []
    if (customerFilter.value !== 'all') pills.push({ key: 'customer', label: `Customer: ${customerFilter.value}` })
    if (statusFilter.value !== 'all') pills.push({ key: 'status', label: `Status: ${statusFilter.value.charAt(0).toUpperCase() + statusFilter.value.slice(1)}` })
    if (dateFilter.value !== 'all') pills.push({ key: 'date', label: `Date: ${dateFilter.value === 'quarter' ? 'This Quarter' : 'This Month'}` })
    return pills
  })

  function removePill(key: string): void {
    if (key === 'customer') customerFilter.value = 'all'
    if (key === 'status') statusFilter.value = 'all'
    if (key === 'date') dateFilter.value = 'all'
  }

  function clearAllFilters(): void {
    customerFilter.value = 'all'
    statusFilter.value = 'all'
    dateFilter.value = 'all'
    search.value = ''
  }

  function toggleSort(key: QuotationSortKey): void {
    if (sortKey.value === key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    else { sortKey.value = key; sortDir.value = 'asc' }
  }

  function setPage(index: number): void {
    pageIndex.value = Math.min(Math.max(index, 0), pageCount.value - 1)
  }

  watch([debouncedSearch, activeTab, customerFilter, statusFilter, dateFilter, pageSize], () => {
    pageIndex.value = 0
  })

  const showingLabel = computed(() => {
    if (totalFiltered.value === 0) return `Showing 0 of ${rows.value.length} quotations`
    const start = pageIndex.value * pageSize.value + 1
    const end = Math.min(start + pageSize.value - 1, totalFiltered.value)
    return `Showing ${start}–${end} of ${totalFiltered.value} quotations`
  })

  return {
    tabs, rows, status, error, fetchQuotations,
    search, debouncedSearch, activeTab, customerFilter, statusFilter, dateFilter, customers,
    sortKey, sortDir, toggleSort, pageIndex, pageSize, pageCount, setPage, pageRows, totalFiltered,
    activePills, removePill, clearAllFilters, showingLabel,
  }
})
