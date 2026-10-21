<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight, Search, Truck, X } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { DispatchTrip } from '@/types/dashboard'
import { useDebounce } from '@/composables/useDebounce'
import DispatchRowItem from './DispatchRowItem.vue'

const props = withDefaults(
  defineProps<{
    trips: DispatchTrip[]
    loading?: boolean
  }>(),
  {
    trips: () => [],
    loading: false,
  },
)

const searchQuery = ref('')
const debouncedSearchQuery = useDebounce(searchQuery, 300)
const selectedFilter = ref<'all' | 'unassigned' | 'in-transit' | 'loading' | 'scheduled'>('all')

const filteredTrips = computed(() => {
  let list = props.trips

  // Status Filter
  if (selectedFilter.value === 'unassigned') {
    list = list.filter((t) => !t.truck || t.truck === 'Unassigned' || !t.driver || t.status === 'pending')
  } else if (selectedFilter.value !== 'all') {
    list = list.filter((t) => t.status === selectedFilter.value)
  }

  // Search Filter
  const q = debouncedSearchQuery.value.trim().toLowerCase()
  if (!q) return list

  return list.filter((t) => {
    return (
      t.id.toLowerCase().includes(q) ||
      t.customer.toLowerCase().includes(q) ||
      t.material.toLowerCase().includes(q) ||
      t.origin.toLowerCase().includes(q) ||
      t.destination.toLowerCase().includes(q) ||
      t.truck.toLowerCase().includes(q) ||
      t.driver.toLowerCase().includes(q)
    )
  })
})

const unassignedCount = computed(() => {
  return props.trips.filter((t) => !t.truck || t.truck === 'Unassigned' || !t.driver || t.status === 'pending').length
})
</script>

<template>
  <Card class="flex flex-col h-full overflow-hidden">
    <!-- Header -->
    <CardHeader class="flex flex-col gap-3 border-b border-border/70 pb-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-2.5">
        <CardTitle class="text-base font-bold tracking-tight text-foreground">
          Today's Dispatch
        </CardTitle>
        <span class="inline-flex items-center rounded-full bg-[#0466C8]/10 px-2 py-0.5 text-xs font-bold text-[#023E7D]">
          {{ trips.length }}
        </span>
        <span
          v-if="unassignedCount > 0"
          class="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[11px] font-bold text-amber-800 border border-amber-500/20"
        >
          {{ unassignedCount }} Unassigned
        </span>
      </div>

      <div class="flex items-center gap-3">
        <!-- Quick Search -->
        <div class="relative w-full max-w-[200px]">
          <Search class="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Filter trips…"
            class="h-8 w-full rounded-lg border border-border/80 bg-muted/50 pl-8 pr-7 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 focus:border-primary transition"
          />
          <button
            v-if="searchQuery"
            type="button"
            class="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-slate-600 rounded-full cursor-pointer"
            title="Clear search"
            @click="searchQuery = ''"
          >
            <X class="size-3" />
          </button>
        </div>

        <RouterLink
          to="/dispatch-board"
          class="inline-flex items-center gap-1 text-xs font-bold text-foreground transition-colors hover:text-[#0466C8]"
        >
          <span>View all</span>
          <ArrowRight class="size-3.5" aria-hidden="true" />
        </RouterLink>
      </div>
    </CardHeader>

    <!-- Filter Tabs Strip -->
    <div class="flex items-center gap-1 border-b border-border/60 bg-muted/20 px-4 py-2 overflow-x-auto text-xs">
      <button
        type="button"
        class="rounded-full px-2.5 py-1 font-semibold transition-colors cursor-pointer"
        :class="selectedFilter === 'all' ? 'bg-[#001233] text-white shadow-2xs' : 'text-muted-foreground hover:text-foreground'"
        @click="selectedFilter = 'all'"
      >
        All ({{ trips.length }})
      </button>
      <button
        type="button"
        class="rounded-full px-2.5 py-1 font-semibold transition-colors cursor-pointer"
        :class="selectedFilter === 'unassigned' ? 'bg-amber-600 text-white shadow-2xs' : 'text-muted-foreground hover:text-foreground'"
        @click="selectedFilter = 'unassigned'"
      >
        Unassigned ({{ unassignedCount }})
      </button>
      <button
        type="button"
        class="rounded-full px-2.5 py-1 font-semibold transition-colors cursor-pointer"
        :class="selectedFilter === 'in-transit' ? 'bg-[#0466C8] text-white shadow-2xs' : 'text-muted-foreground hover:text-foreground'"
        @click="selectedFilter = 'in-transit'"
      >
        In Transit
      </button>
      <button
        type="button"
        class="rounded-full px-2.5 py-1 font-semibold transition-colors cursor-pointer"
        :class="selectedFilter === 'loading' ? 'bg-amber-500 text-white shadow-2xs' : 'text-muted-foreground hover:text-foreground'"
        @click="selectedFilter = 'loading'"
      >
        Loading
      </button>
      <button
        type="button"
        class="rounded-full px-2.5 py-1 font-semibold transition-colors cursor-pointer"
        :class="selectedFilter === 'scheduled' ? 'bg-[#023E7D] text-white shadow-2xs' : 'text-muted-foreground hover:text-foreground'"
        @click="selectedFilter = 'scheduled'"
      >
        Scheduled
      </button>
    </div>

    <!-- Content Area with Staggered Transition -->
    <CardContent class="p-0 flex-1 overflow-y-auto max-h-[520px]">
      <!-- Shimmer Skeleton Loading -->
      <div v-if="loading" class="divide-y divide-border/60 p-4 space-y-4 animate-pulse">
        <div v-for="i in 5" :key="i" class="flex items-center justify-between py-2">
          <div class="space-y-2">
            <div class="h-4 w-28 rounded bg-muted/80" />
            <div class="h-3 w-44 rounded bg-muted/60" />
          </div>
          <div class="h-4 w-48 rounded bg-muted/50 hidden sm:block" />
          <div class="h-7 w-20 rounded-full bg-muted/70" />
        </div>
      </div>

      <!-- Real Rows -->
      <div v-else-if="filteredTrips.length > 0" class="divide-y divide-border/50">
        <DispatchRowItem
          v-for="(trip, index) in filteredTrips"
          :key="trip.id"
          :trip="trip"
          :index="index"
        />
      </div>

      <!-- Empty State -->
      <div v-else class="flex flex-col items-center justify-center py-16 text-center px-4">
        <div class="size-12 rounded-full bg-muted/60 flex items-center justify-center text-muted-foreground mb-3">
          <Truck class="size-6" />
        </div>
        <p class="text-sm font-bold text-foreground">No dispatch trips found</p>
        <p class="text-xs text-muted-foreground max-w-xs mt-1">
          {{ searchQuery ? `No records matching "${searchQuery}".` : 'No active trips under this filter.' }}
        </p>
        <button
          v-if="searchQuery || selectedFilter !== 'all'"
          type="button"
          class="mt-3 text-xs font-semibold text-[#0466C8] hover:underline cursor-pointer"
          @click="searchQuery = ''; selectedFilter = 'all'"
        >
          Reset filters
        </button>
      </div>
    </CardContent>
  </Card>
</template>

