<script setup lang="ts">
import { computed } from 'vue'

import type { BoardColumnDef, BoardTrip } from '@/types/board'

import TripCard from './TripCard.vue'

const props = defineProps<{
  column: BoardColumnDef
  trips: BoardTrip[]
  hiddenCount?: number
}>()

const shownTrips = computed(() => props.trips.slice(0, 3))
</script>

<template>
  <section
    class="flex w-[272px] shrink-0 flex-col gap-3 rounded-2xl bg-muted/50 p-3"
    :aria-label="`${column.label} column, ${trips.length} trips`"
  >
    <header class="flex items-center justify-between gap-2 px-1">
      <h2 class="flex items-center gap-2 text-sm font-bold">
        <span class="size-2 rounded-full" :class="column.dotClass" aria-hidden="true" />
        {{ column.label }}
      </h2>
      <span class="rounded-full bg-white px-2.5 py-0.5 text-xs font-bold shadow-sm">
        {{ trips.length }}
      </span>
    </header>

    <TripCard v-for="trip in shownTrips" :key="trip.id" :trip="trip" />

    <p v-if="hiddenCount" class="pb-1 text-center text-xs font-medium text-muted-foreground">
      + {{ hiddenCount }} more trips
    </p>
  </section>
</template>