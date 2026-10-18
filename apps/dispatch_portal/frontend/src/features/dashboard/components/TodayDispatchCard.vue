<script setup lang="ts">
import { ArrowRight, MapPin } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/shared/StatusBadge.vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { DispatchTrip } from '@/types/dashboard'

defineProps<{ trips: DispatchTrip[] }>()
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Today's Dispatch</CardTitle>
      <RouterLink
        to="/dispatch-board"
        class="flex items-center gap-1 text-sm font-bold text-lime-700 transition-colors hover:text-lime-800"
      >
        View all
        <ArrowRight class="size-4" aria-hidden="true" />
      </RouterLink>
    </CardHeader>
    <CardContent class="space-y-1">
      <div
        v-for="(trip, index) in trips"
        :key="trip.id"
        class="flex items-center justify-between gap-4 rounded-xl px-3 py-3 transition-colors hover:bg-muted/60"
        :class="{ 'border-t': index > 0 }"
      >
        <div class="min-w-0">
          <p class="text-sm font-bold tracking-tight">{{ trip.id }}</p>
          <p class="mt-0.5 truncate text-[13px] text-muted-foreground">
            {{ trip.customer }} · {{ trip.material }}
          </p>
        </div>

        <div class="hidden min-w-0 flex-1 sm:block">
          <p class="flex items-center gap-1.5 text-[13px] font-semibold">
            <MapPin class="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
            <span class="truncate">{{ trip.origin }} → {{ trip.destination }}</span>
          </p>
          <p class="mt-0.5 pl-5 text-xs text-muted-foreground">{{ trip.truck }} · {{ trip.driver }}</p>
        </div>

        <div class="flex shrink-0 flex-col items-end gap-1.5">
          <p class="text-[13px] font-medium text-muted-foreground">{{ trip.timeLabel }}</p>
          <StatusBadge :status="trip.status" />
        </div>
      </div>
    </CardContent>
  </Card>
</template>
