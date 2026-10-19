<script setup lang="ts">
import { ChevronDown, LayoutGrid, List, Plus, Search } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/shared/LoadingState.vue'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { useDispatchBoardStore } from '@/stores/dispatchBoard'
import type { BoardTrip } from '@/types/board'

import BoardColumn from './BoardColumn.vue'

const router = useRouter()
const store = useDispatchBoardStore()

onMounted(() => {
  void store.fetchBoard()
})

const search = ref('')

const filteredTrips = computed<BoardTrip[]>(() => {
  const q = search.value.trim().toLowerCase()
  const trips = store.data?.trips ?? []
  if (!q) return trips
  return trips.filter((t) =>
    [t.id, t.customer, t.origin, t.destination, t.detail].some((f) =>
      f.toLowerCase().includes(q),
    ),
  )
})

function tripsFor(columnKey: string): BoardTrip[] {
  return filteredTrips.value.filter((t) => t.column === columnKey)
}

const metaLabel = computed(
  () => `${store.columnCount} columns · ${store.totalTrips} trips`,
)
</script>

<template>
  <PageContainer>
    <PageHeader
      title="Dispatch Board"
      subtitle="Trips grouped by operational status · status changes follow backend permissions"
    >
      <template #actions>
        <div class="flex rounded-xl border bg-card p-1 shadow-sm" role="tablist" aria-label="View mode">
          <button
            type="button"
            role="tab"
            :aria-selected="true"
            class="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white shadow-sm"
          >
            <LayoutGrid class="size-4" aria-hidden="true" />
            Board
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="false"
            class="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-bold text-muted-foreground transition-colors hover:text-foreground"
            @click="router.push('/dispatch-board/table')"
          >
            <List class="size-4" aria-hidden="true" />
            Table
          </button>
        </div>
        <Button size="lg" class="rounded-lg" @click="router.push('/create-trip')">
          <Plus aria-hidden="true" />
          Create Trip
        </Button>
      </template>
    </PageHeader>

    <!-- Toolbar -->
    <div class="mb-4 flex flex-wrap items-center gap-3 rounded-2xl border bg-card p-3 shadow-sm">
      <div class="relative min-w-[220px] flex-1">
        <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <input
          v-model="search"
          type="search"
          placeholder="Search trip, customer, truck…"
          aria-label="Search trips"
          class="h-10 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
      <div class="ml-auto hidden items-center gap-2 sm:flex">
        <button type="button" class="flex h-10 items-center gap-1.5 rounded-full border bg-background px-4 text-sm font-bold shadow-sm hover:bg-accent" disabled>
          Today · 12 May <ChevronDown class="size-4" aria-hidden="true" />
        </button>
        <button type="button" class="flex h-10 items-center gap-1.5 rounded-full border bg-background px-4 text-sm font-bold shadow-sm hover:bg-accent" disabled>
          All Statuses <ChevronDown class="size-4" aria-hidden="true" />
        </button>
        <button type="button" class="flex h-10 items-center gap-1.5 rounded-full border bg-background px-4 text-sm font-bold shadow-sm hover:bg-accent" disabled>
          All Customers <ChevronDown class="size-4" aria-hidden="true" />
        </button>
      </div>
      <p class="hidden text-sm text-muted-foreground md:block">{{ metaLabel }}</p>
    </div>

    <LoadingState v-if="store.status === 'loading' || store.status === 'idle'" label="Loading dispatch board…" />

    <div
      v-else-if="store.status === 'success' && store.data"
      class="flex gap-4 overflow-x-auto pb-4"
    >
      <BoardColumn
        v-for="column in store.data.columns"
        :key="column.key"
        :column="column"
        :trips="tripsFor(column.key)"
        :hidden-count="store.data.hiddenCounts[column.key]"
      />
    </div>

    <div v-else class="rounded-2xl border bg-card shadow-sm">
      <ErrorState :description="store.error ?? undefined" @retry="store.fetchBoard()" />
    </div>
  </PageContainer>
</template>
