<script setup lang="ts">
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Check,
  Download,
  LayoutGrid,
  List,
  Plus,
  Search,
  SlidersHorizontal,
  UserPlus,
  X,
} from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/shared/LoadingState.vue'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { useDispatchTableStore } from '@/stores/dispatchTable'
import type { TableTripStatus } from '@/types/dispatchTable'

const router = useRouter()
const store = useDispatchTableStore()

onMounted(() => {
  void store.fetchTrips()
})

const statusStyle: Record<TableTripStatus, { label: string; text: string; dot: string }> = {
  'in-transit': { label: 'In Transit', text: 'text-blue-700', dot: 'bg-blue-600' },
  loading: { label: 'Loading', text: 'text-amber-600', dot: 'bg-amber-600' },
  scheduled: { label: 'Scheduled', text: 'text-blue-700', dot: 'bg-blue-600' },
  unassigned: { label: 'Unassigned', text: 'text-amber-600', dot: 'bg-amber-600' },
  delivered: { label: 'Delivered', text: 'text-emerald-600', dot: 'bg-emerald-600' },
  completed: { label: 'Completed', text: 'text-emerald-600', dot: 'bg-emerald-600' },
}

const metaLabel = computed(() => {
  const meta = store.data?.meta
  if (!meta) return ''
  return `${meta.totalToday} trips today · ${meta.inTransit} in transit · ${meta.ratePending} rate pending`
})

/** Sortable header cell helper */
function headerClass(key: 'id' | 'window') {
  return [
    'select-none cursor-pointer px-3 py-4 text-[13px] font-bold uppercase tracking-wide text-muted-foreground hover:text-foreground',
    store.sortKey === key ? 'text-foreground' : '',
  ]
}

function sortIcon(key: 'id' | 'window') {
  if (store.sortKey !== key) return ArrowUpDown
  return store.sortDir === 'asc' ? ArrowUp : ArrowDown
}

/** Real client-side CSV export of the selected rows. */
function exportSelected() {
  const rows = store.selectedTrips
  if (rows.length === 0) return
  const header = ['Trip No.', 'Status', 'Customer', 'Route', 'Truck', 'Driver', 'Material', 'Qty', 'Window', 'Rate']
  const lines = rows.map((t) =>
    [t.id, statusStyle[t.status].label, t.customer, t.route, t.truck ?? '—', t.driver ?? '—', t.material, t.qty, t.window, t.rate ?? 'Pending']
      .map((c) => `"${String(c).replaceAll('"', '""')}"`).join(','),
  )
  const csv = [header.join(','), ...lines].join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = 'dispatch-selected-trips.csv'
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <PageContainer>
    <PageHeader
      title="Dispatch — Table View"
      subtitle="Every trip in one filterable grid · same live data as the board"
    >
      <template #actions>
        <!-- View toggle: Board | Table -->
        <div class="flex rounded-xl border bg-card p-1 shadow-sm" role="tablist" aria-label="View mode">
          <button
            type="button"
            role="tab"
            :aria-selected="false"
            class="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-bold text-muted-foreground transition-colors hover:text-foreground"
            @click="router.push('/dispatch-board')"
          >
            <LayoutGrid class="size-4" aria-hidden="true" />
            Board
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="true"
            class="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white shadow-sm"
          >
            <List class="size-4" aria-hidden="true" />
            Table
          </button>
        </div>
        <Button size="lg" class="rounded-lg" @click="router.push('/create-trip')">
          <Plus aria-hidden="true" />
          Create Trip
        </Button>
        <Button size="lg" variant="outline" class="rounded-lg" disabled title="Full export arrives with backend integration">
          <Download aria-hidden="true" />
          Export
        </Button>
      </template>
    </PageHeader>

    <!-- Filter toolbar -->
    <div class="mb-3 flex flex-wrap items-center gap-3 rounded-2xl border bg-card p-3 shadow-sm">
      <div class="relative min-w-[220px] flex-1">
        <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <input
          v-model="store.search"
          type="search"
          placeholder="Search trip, customer, plate…"
          aria-label="Search trips"
          class="h-10 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
      <div class="hidden items-center gap-2 lg:flex">
        <button v-for="chip in ['Date: Today', 'Status: All', 'Material: All', 'Customer: All', 'Emirate: All']" :key="chip" type="button"
          class="flex h-9 items-center gap-1 rounded-full border bg-background px-3.5 text-[13px] font-bold shadow-sm hover:bg-accent"
          disabled
          :title="`${chip} — server-side filter, enabled with backend integration`"
        >
          {{ chip }} <ArrowDown class="size-3.5" aria-hidden="true" />
        </button>
      </div>
      <button type="button" class="ml-auto text-sm font-semibold text-muted-foreground hover:text-foreground" @click="store.search = ''">
        Reset
      </button>
      <Button variant="outline" size="lg" class="rounded-lg" disabled title="More filters arrive with backend integration">
        <SlidersHorizontal aria-hidden="true" />
        More Filters
      </Button>
    </div>

    <!-- Active filter pills + meta -->
    <div class="mb-4 flex flex-wrap items-center gap-2.5">
      <span
        v-for="filter in store.activeFilters"
        :key="filter.label"
        class="flex items-center gap-1.5 rounded-full border border-lime-300 bg-lime-50 px-3.5 py-1.5 text-[13px] font-bold text-lime-800"
      >
        {{ filter.label }}
        <button
          type="button"
          :aria-label="`Remove filter ${filter.label}`"
          class="rounded-full p-0.5 hover:bg-lime-200"
          @click="store.removeFilter(filter.label)"
        >
          <X class="size-3.5" aria-hidden="true" />
        </button>
      </span>
      <button
        v-if="store.activeFilters.length"
        type="button"
        class="text-[13px] font-bold text-lime-700 hover:underline"
        @click="store.clearFilters()"
      >
        Clear all
      </button>
      <p class="ml-auto text-sm text-muted-foreground">{{ metaLabel }}</p>
    </div>

    <!-- Table -->
    <LoadingState v-if="store.status === 'loading' || store.status === 'idle'" label="Loading trips…" />

    <template v-else-if="store.status === 'success' && store.data">
      <div class="overflow-x-auto rounded-2xl border bg-card shadow-sm">
        <table class="w-full min-w-[1100px] border-collapse text-sm">
          <thead>
            <tr class="text-left">
              <th scope="col" class="w-12 px-4 py-4">
                <button
                  type="button"
                  role="checkbox"
                  :aria-checked="store.allVisibleSelected"
                  :aria-label="store.allVisibleSelected ? 'Deselect all visible trips' : 'Select all visible trips'"
                  class="flex size-4.5 items-center justify-center rounded border-2 border-muted-foreground/40 transition-colors"
                  :class="store.allVisibleSelected ? 'border-primary bg-primary' : 'bg-background'"
                  @click="store.toggleAllVisible()"
                >
                  <Check v-if="store.allVisibleSelected" class="size-3 text-primary-foreground" aria-hidden="true" />
                </button>
              </th>
              <th scope="col" :class="headerClass('id')" @click="store.toggleSort('id')">
                <span class="inline-flex items-center gap-1">
                  Trip No.
                  <component :is="sortIcon('id')" class="size-3.5" aria-hidden="true" />
                </span>
              </th>
              <th scope="col" class="px-3 py-4 text-[13px] font-bold uppercase tracking-wide text-muted-foreground">Status</th>
              <th scope="col" class="px-3 py-4 text-[13px] font-bold uppercase tracking-wide text-muted-foreground">Customer</th>
              <th scope="col" class="px-3 py-4 text-[13px] font-bold uppercase tracking-wide text-muted-foreground">Loading → Destination</th>
              <th scope="col" class="px-3 py-4 text-[13px] font-bold uppercase tracking-wide text-muted-foreground">Truck</th>
              <th scope="col" class="px-3 py-4 text-[13px] font-bold uppercase tracking-wide text-muted-foreground">Driver</th>
              <th scope="col" class="px-3 py-4 text-[13px] font-bold uppercase tracking-wide text-muted-foreground">Material · Qty</th>
              <th scope="col" :class="headerClass('window')" @click="store.toggleSort('window')">
                <span class="inline-flex items-center gap-1">
                  Window
                  <component :is="sortIcon('window')" class="size-3.5" aria-hidden="true" />
                </span>
              </th>
              <th scope="col" class="px-4 py-4 text-right text-[13px] font-bold uppercase tracking-wide text-muted-foreground">Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="trip in store.visibleTrips"
              :key="trip.id"
              class="border-t transition-colors"
              :class="store.selectedIds.has(trip.id) ? 'bg-lime-50' : 'hover:bg-muted/40'"
            >
              <td class="px-4 py-4">
                <button
                  type="button"
                  role="checkbox"
                  :aria-checked="store.selectedIds.has(trip.id)"
                  :aria-label="`Select trip ${trip.id}`"
                  class="flex size-4.5 items-center justify-center rounded border-2 transition-colors"
                  :class="store.selectedIds.has(trip.id) ? 'border-primary bg-primary' : 'border-muted-foreground/40 bg-background'"
                  @click="store.toggleTrip(trip.id)"
                >
                  <Check v-if="store.selectedIds.has(trip.id)" class="size-3 text-primary-foreground" aria-hidden="true" />
                </button>
              </td>
              <td class="px-3 py-4 font-bold tracking-tight">{{ trip.id }}</td>
              <td class="px-3 py-4">
                <span class="flex items-center gap-1.5 text-[13px] font-bold" :class="statusStyle[trip.status].text">
                  <span class="size-1.5 rounded-full" :class="statusStyle[trip.status].dot" aria-hidden="true" />
                  {{ statusStyle[trip.status].label }}
                </span>
              </td>
              <td class="px-3 py-4">{{ trip.customer }}</td>
              <td class="px-3 py-4 text-muted-foreground">{{ trip.route }}</td>
              <td class="px-3 py-4">{{ trip.truck ?? '—' }}</td>
              <td class="px-3 py-4">{{ trip.driver ?? '—' }}</td>
              <td class="px-3 py-4">{{ trip.material }} · {{ trip.qty }}</td>
              <td class="px-3 py-4 text-muted-foreground">{{ trip.window }}</td>
              <td class="px-4 py-4 text-right font-bold" :class="trip.rate ? '' : 'font-semibold text-amber-600'">
                {{ trip.rate ?? 'Pending' }}
              </td>
            </tr>
            <tr v-if="store.visibleTrips.length === 0">
              <td colspan="10" class="px-4 py-10 text-center text-sm text-muted-foreground">
                No trips match your search.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Bulk action bar -->
      <div
        v-if="store.selectedIds.size > 0"
        class="sticky bottom-4 mt-4 flex flex-wrap items-center gap-3 rounded-2xl bg-slate-900 px-5 py-3.5 text-white shadow-lg"
        role="region"
        aria-label="Bulk actions"
      >
        <span class="flex items-center gap-2 text-sm font-bold">
          <span class="flex size-5 items-center justify-center rounded bg-primary" aria-hidden="true">
            <Check class="size-3 text-primary-foreground" />
          </span>
          {{ store.selectedIds.size }} trip{{ store.selectedIds.size === 1 ? '' : 's' }} selected
        </span>
        <div class="ml-auto flex items-center gap-2.5">
          <button type="button" class="text-sm font-semibold text-white/70 hover:text-white" @click="store.clearSelection()">
            Clear
          </button>
          <Button variant="outline" size="lg" class="rounded-lg border-white/25 bg-transparent text-white hover:bg-white/10 hover:text-white" @click="exportSelected">
            <Download aria-hidden="true" />
            Export Selected
          </Button>
          <Button size="lg" class="rounded-lg" @click="router.push('/create-trip')">
            <UserPlus aria-hidden="true" />
            Assign Driver
          </Button>
        </div>
      </div>
    </template>

    <div v-else class="rounded-2xl border bg-card shadow-sm">
      <ErrorState :description="store.error ?? undefined" @retry="store.fetchTrips()" />
    </div>
  </PageContainer>
</template>