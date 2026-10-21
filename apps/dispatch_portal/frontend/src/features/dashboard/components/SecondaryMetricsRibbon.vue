<script setup lang="ts">
import { useRouter } from 'vue-router'
import { AlertTriangle, CalendarCheck, CheckCircle2, ChevronRight, Users } from 'lucide-vue-next'
import { useAnimatedNumber } from '@/composables/useAnimatedNumber'

interface Props {
  scheduled: number
  scheduledNote?: string
  completed: number
  completedNote?: string
  needAttention: number
  exceptionCount?: number
  podPendingCount?: number
  driversAvailable: number
  driversNote?: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  scheduled: 0,
  scheduledNote: 'Assigned & ready',
  completed: 0,
  completedNote: 'Delivered today',
  needAttention: 0,
  exceptionCount: 0,
  podPendingCount: 0,
  driversAvailable: 0,
  driversNote: 'Active roster',
  loading: false,
})

const router = useRouter()

const animScheduled = useAnimatedNumber(() => props.scheduled, 600)
const animCompleted = useAnimatedNumber(() => props.completed, 600)
const animAttention = useAnimatedNumber(() => props.needAttention, 600)
const animDrivers = useAnimatedNumber(() => props.driversAvailable, 600)

function navigateWithFilter(filterKey: string) {
  router.push({
    path: '/dispatch-board',
    query: { filter: filterKey },
  })
}
</script>

<template>
  <div class="overflow-hidden rounded-2xl border border-border/80 bg-card/90 backdrop-blur-md shadow-xs">
    <div class="grid grid-cols-2 divide-y divide-border/60 sm:grid-cols-4 sm:divide-x sm:divide-y-0">
      <!-- 1. Scheduled -->
      <button
        type="button"
        class="group flex flex-col justify-between p-4 text-left transition-colors hover:bg-muted/50 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
        title="View scheduled trips on Dispatch Board"
        @click="navigateWithFilter('scheduled')"
      >
        <div class="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span class="flex items-center gap-1.5">
            <CalendarCheck class="size-3.5 text-[#0466C8]" aria-hidden="true" />
            Scheduled
          </span>
          <ChevronRight class="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-2xl font-bold tracking-tight text-foreground">
            {{ animScheduled }}
          </span>
          <span class="truncate text-[11px] font-medium text-muted-foreground">
            {{ scheduledNote }}
          </span>
        </div>
      </button>

      <!-- 2. Completed -->
      <button
        type="button"
        class="group flex flex-col justify-between p-4 text-left transition-colors hover:bg-muted/50 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
        title="View completed trips on Dispatch Board"
        @click="navigateWithFilter('completed')"
      >
        <div class="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span class="flex items-center gap-1.5">
            <CheckCircle2 class="size-3.5 text-emerald-600" aria-hidden="true" />
            Completed
          </span>
          <ChevronRight class="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-2xl font-bold tracking-tight text-foreground">
            {{ animCompleted }}
          </span>
          <span class="truncate text-[11px] font-medium text-emerald-700">
            {{ completedNote }}
          </span>
        </div>
      </button>

      <!-- 3. Need Attention (Alert Highlight) -->
      <button
        type="button"
        class="group relative flex flex-col justify-between p-4 text-left transition-colors hover:bg-rose-500/5 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500/20"
        :class="{ 'bg-rose-500/[0.03]': needAttention > 0 }"
        title="View trips needing attention"
        @click="navigateWithFilter('attention')"
      >
        <div class="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span class="flex items-center gap-1.5" :class="needAttention > 0 ? 'text-rose-600 font-bold' : ''">
            <span v-if="needAttention > 0" class="relative flex size-2">
              <span class="absolute inline-flex size-full animate-ping rounded-full bg-rose-400 opacity-75" />
              <span class="relative inline-flex size-2 rounded-full bg-rose-500" />
            </span>
            <AlertTriangle v-else class="size-3.5 text-amber-500" aria-hidden="true" />
            Need Attention
          </span>
          <ChevronRight class="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-2xl font-bold tracking-tight" :class="needAttention > 0 ? 'text-rose-600' : 'text-foreground'">
            {{ animAttention }}
          </span>
          <span class="truncate text-[11px] font-semibold" :class="needAttention > 0 ? 'text-rose-700' : 'text-muted-foreground'">
            {{ exceptionCount ? `${exceptionCount} exceptions` : '' }}
            {{ podPendingCount ? `${exceptionCount ? ' · ' : ''}${podPendingCount} POD` : '' }}
            {{ !exceptionCount && !podPendingCount ? 'All systems clear' : '' }}
          </span>
        </div>
      </button>

      <!-- 4. Drivers Available -->
      <button
        type="button"
        class="group flex flex-col justify-between p-4 text-left transition-colors hover:bg-muted/50 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
        title="View driver availability"
        @click="navigateWithFilter('drivers')"
      >
        <div class="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span class="flex items-center gap-1.5">
            <Users class="size-3.5 text-foreground" aria-hidden="true" />
            Drivers Available
          </span>
          <ChevronRight class="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-2xl font-bold tracking-tight text-foreground">
            {{ animDrivers }}
          </span>
          <span class="truncate text-[11px] font-medium text-muted-foreground">
            {{ driversNote }}
          </span>
        </div>
      </button>
    </div>
  </div>
</template>

