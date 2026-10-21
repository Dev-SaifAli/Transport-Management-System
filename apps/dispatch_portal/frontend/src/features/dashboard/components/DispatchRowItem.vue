<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, ChevronRight, Truck } from 'lucide-vue-next'
import StatusBadge from '@/components/shared/StatusBadge.vue'
import type { DispatchTrip } from '@/types/dashboard'

const props = defineProps<{
  trip: DispatchTrip
  index: number
}>()

const router = useRouter()

const isUnassigned = computed(() => {
  return !props.trip.truck || props.trip.truck === 'Unassigned' || !props.trip.driver || props.trip.status === 'pending'
})

const driverInitials = computed(() => {
  if (!props.trip.driver || props.trip.driver === 'Unassigned') return '—'
  const parts = props.trip.driver.trim().split(/\s+/)
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  return props.trip.driver.slice(0, 2).toUpperCase()
})

function handleRowClick() {
  if (isUnassigned.value) {
    router.push({
      path: '/create-trip',
      query: { tripId: props.trip.id },
    })
  } else {
    router.push({
      path: '/dispatch-board',
      query: { search: props.trip.id },
    })
  }
}
</script>

<template>
  <div
    class="group relative flex flex-col justify-between gap-3 p-4 transition-all duration-200 hover:bg-muted/40 sm:flex-row sm:items-center cursor-pointer border-b border-border/50 last:border-b-0"
    :style="{ animationDelay: `${index * 50}ms` }"
    @click="handleRowClick"
  >
    <!-- Left: Monospace Trip ID + Customer & Material -->
    <div class="flex items-start gap-3 min-w-0 sm:w-[220px] shrink-0">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center rounded-md border border-border/80 bg-background px-2 py-0.5 font-mono text-xs font-bold tracking-tight text-foreground shadow-2xs group-hover:border-[#0466C8]/40">
            {{ trip.id }}
          </span>
          <StatusBadge :status="trip.status" class="sm:hidden" />
        </div>
        <p class="truncate text-xs font-medium text-foreground" :title="trip.customer">
          {{ trip.customer }}
        </p>
        <span class="inline-block truncate text-[11px] font-semibold text-muted-foreground" :title="trip.material">
          {{ trip.material }}
        </span>
      </div>
    </div>

    <!-- Center: Visual Origin-to-Destination Route Connector (o---▸) -->
    <div class="flex-1 min-w-0 px-1 sm:px-4">
      <div class="flex items-center gap-2 text-xs">
        <span class="truncate font-semibold text-foreground max-w-[150px]" :title="trip.origin">
          {{ trip.origin }}
        </span>

        <!-- Visual Route Connector o---▸ -->
        <div class="flex items-center gap-1 text-muted-foreground/60 shrink-0 px-1" aria-hidden="true">
          <span class="size-1.5 rounded-full bg-[#0466C8]" />
          <div class="w-8 sm:w-16 h-px bg-border group-hover:bg-[#0466C8]/40 transition-colors" />
          <ArrowRight class="size-3 text-[#0466C8]" />
        </div>

        <span class="truncate font-bold text-foreground max-w-[150px]" :title="trip.destination">
          {{ trip.destination }}
        </span>
      </div>

      <!-- Truck & Driver Meta Chips -->
      <div class="mt-1.5 flex flex-wrap items-center gap-2 text-[11px]">
        <!-- Truck Plate Pill -->
        <span
          v-if="trip.truck && trip.truck !== 'Unassigned'"
          class="inline-flex items-center gap-1 rounded bg-muted/80 px-1.5 py-0.5 font-mono text-[10px] font-bold text-foreground border border-border/60"
        >
          <Truck class="size-2.5 text-muted-foreground" aria-hidden="true" />
          {{ trip.truck }}
        </span>
        <span v-else class="text-[11px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
          No Truck
        </span>

        <!-- Driver Avatar Chip -->
        <div v-if="trip.driver && trip.driver !== 'Unassigned'" class="flex items-center gap-1 text-muted-foreground">
          <span class="flex size-4.5 items-center justify-center rounded-full bg-[#001233] text-[9px] font-bold text-white">
            {{ driverInitials }}
          </span>
          <span class="truncate max-w-[110px]">{{ trip.driver }}</span>
        </div>
        <span v-else class="text-[11px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
          No Driver
        </span>

        <span v-if="trip.timeLabel" class="text-muted-foreground/80 font-mono text-[10px] ml-auto sm:ml-0">
          {{ trip.timeLabel }}
        </span>
      </div>
    </div>

    <!-- Right: Status Badge on Desktop + Inline Hover Action Button -->
    <div class="flex items-center justify-between sm:justify-end gap-3 shrink-0">
      <StatusBadge :status="trip.status" class="hidden sm:inline-flex" />

      <!-- Hover Action Button: Reveal on hover -->
      <div class="flex items-center">
        <button
          v-if="isUnassigned"
          type="button"
          class="inline-flex items-center gap-1 rounded-full bg-[#0466C8] px-3.5 py-1 text-xs font-bold text-white shadow-2xs transition-all hover:bg-[#0353A4] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 cursor-pointer"
          @click.stop="handleRowClick"
        >
          <span>Assign</span>
          <ArrowRight class="size-3" aria-hidden="true" />
        </button>
        <button
          v-else
          type="button"
          class="inline-flex items-center gap-1 rounded-full border border-border/80 bg-background px-3 py-1 text-xs font-semibold text-foreground shadow-2xs transition-all hover:bg-muted group-hover:border-[#0466C8]/30 group-hover:text-[#0466C8] cursor-pointer"
          @click.stop="handleRowClick"
        >
          <span>View</span>
          <ChevronRight class="size-3" aria-hidden="true" />
        </button>
      </div>
    </div>
  </div>
</template>

