<script setup lang="ts">
import { ArrowRight, MapPin } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/shared/StatusBadge.vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { DispatchTrip } from '@/types/dashboard'

defineProps<{ trips: DispatchTrip[] }>()
</script>

<template>
  <Card class="flex flex-col h-full">
    <CardHeader class="flex items-center justify-between border-b border-border/70 pb-3">
      <CardTitle class="text-base font-bold tracking-tight text-foreground">Today's Dispatch</CardTitle>
      <RouterLink
        to="/dispatch-board"
        class="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-bold text-foreground transition-colors hover:text-foreground/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        View all
        <ArrowRight class="size-3.5" aria-hidden="true" />
      </RouterLink>
    </CardHeader>
    <CardContent class="divide-y divide-border/60 p-0">
      <div v-if="trips.length === 0" class="py-10 text-center">
        <p class="text-xs font-medium text-muted-foreground">No active trips dispatched for today.</p>
      </div>

      <div
        v-for="trip in trips"
        :key="trip.id"
        class="group flex items-center justify-between gap-4 px-5 py-3.5 transition-colors hover:bg-muted/40"
      >
        <!-- Trip ID and client/cargo -->
        <div class="min-w-0 max-w-[170px] shrink-0 sm:max-w-[200px]">
          <p class="font-mono text-sm font-bold tracking-tight text-foreground group-hover:text-foreground">
            {{ trip.id }}
          </p>
          <p class="mt-0.5 truncate text-xs text-muted-foreground" :title="`${trip.customer} · ${trip.material}`">
            {{ trip.customer }} · {{ trip.material }}
          </p>
          <!-- Mobile route fallback -->
          <div class="mt-1 flex flex-col gap-0.5 text-[11px] sm:hidden">
            <div class="flex items-center gap-1 text-neutral-600">
              <MapPin class="size-3 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span class="font-medium text-neutral-700">{{ trip.origin }}</span>
              <span class="text-neutral-400">→</span>
              <span class="font-bold text-neutral-900">{{ trip.destination }}</span>
            </div>
            <p class="pl-4 text-[10px] text-muted-foreground">
              {{ trip.truck }} · {{ trip.driver }}
            </p>
          </div>
        </div>

        <!-- Route & Vehicle/Driver (Tablet/Desktop) -->
        <div class="hidden min-w-0 flex-1 px-3 sm:block">
          <div
            class="flex flex-wrap items-center gap-1.5 text-xs font-semibold text-foreground"
            :title="`${trip.origin} → ${trip.destination}`"
          >
            <MapPin class="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
            <span class="font-medium text-neutral-600">{{ trip.origin }}</span>
            <span class="shrink-0 text-muted-foreground/60">→</span>
            <span class="font-bold text-foreground">{{ trip.destination }}</span>
          </div>
          <p
            class="mt-0.5 truncate pl-5 text-[11px] text-muted-foreground"
            :title="`${trip.truck} · ${trip.driver}`"
          >
            {{ trip.truck }} · {{ trip.driver }}
          </p>
        </div>

        <!-- Aligned Time and Status Badge -->
        <div class="flex w-28 shrink-0 flex-col items-end justify-center gap-1 text-right">
          <span class="text-xs font-medium tabular-nums text-muted-foreground">{{ trip.timeLabel }}</span>
          <StatusBadge :status="trip.status" />
        </div>
      </div>
    </CardContent>
  </Card>
</template>
