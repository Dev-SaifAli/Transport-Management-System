<script setup lang="ts">
import { MapPin } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/shared/StatusBadge.vue'
import type { BoardTrip } from '@/types/board'

defineProps<{ trip: BoardTrip }>()
</script>

<template>
  <div class="rounded-xl border bg-card p-4 shadow-sm">
    <p class="text-sm font-bold tracking-tight">{{ trip.id }}</p>
    <p class="mt-0.5 text-[13px] text-muted-foreground">{{ trip.customer }}</p>

    <p class="mt-2.5 flex items-center gap-1.5 text-[13px] font-semibold">
      <MapPin class="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span class="truncate">{{ trip.origin }} → {{ trip.destination }}</span>
    </p>
    <p class="mt-0.5 pl-5 text-xs text-muted-foreground">{{ trip.detail }}</p>

    <!-- Unassigned trips get the primary action instead of a status badge -->
    <RouterLink
      v-if="trip.column === 'unassigned'"
      to="/create-trip"
      class="mt-3 block rounded-lg bg-[#0466C8]/10 py-2 text-center text-xs font-bold text-[#023E7D] transition-colors hover:bg-[#0466C8]/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      Assign Truck &amp; Driver
    </RouterLink>
    <div v-else class="mt-3">
      <StatusBadge :status="trip.column" />
    </div>
  </div>
</template>