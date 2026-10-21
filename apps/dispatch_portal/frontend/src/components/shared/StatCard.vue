<script setup lang="ts">
import {
  AlertCircle,
  AlertTriangle,
  CalendarCheck,
  CheckCircle2,
  IdCard,
  Truck,
  Users,
  type LucideIcon,
} from 'lucide-vue-next'
import { computed } from 'vue'

import { Card } from '@/components/ui/card'
import type { KpiStat } from '@/types/dashboard'

interface Props {
  stat: KpiStat
  priority?: 'primary' | 'secondary'
}

const props = withDefaults(defineProps<Props>(), {
  priority: 'primary',
})

const iconMap: Record<string, LucideIcon> = {
  users: Users,
  'alert-circle': AlertCircle,
  'calendar-check': CalendarCheck,
  truck: Truck,
  'check-circle': CheckCircle2,
  'alert-triangle': AlertTriangle,
  'id-card': IdCard,
}

const Icon = computed(() => iconMap[props.stat.icon] ?? Truck)

const pillClass = computed(() => {
  const cls = props.stat.noteClass || ''
  if (cls.includes('emerald') || cls.includes('lime')) {
    return 'bg-emerald-50 text-emerald-800 border-emerald-200/70'
  }
  if (cls.includes('amber')) {
    return 'bg-amber-50 text-amber-900 border-amber-200/70'
  }
  if (cls.includes('red')) {
    return 'bg-rose-50 text-rose-800 border-rose-200/70'
  }
  if (cls.includes('blue') || cls.includes('deepsea') || cls.includes('0466C8')) {
    return 'bg-[#0466C8]/10 text-[#023E7D] border-[#0466C8]/25'
  }
  return 'bg-muted/70 text-muted-foreground border-border/60'
})

const pillDot = computed(() => {
  const cls = props.stat.noteClass || ''
  if (cls.includes('emerald') || cls.includes('lime')) return 'bg-emerald-500'
  if (cls.includes('amber')) return 'bg-amber-500'
  if (cls.includes('red')) return 'bg-rose-500'
  if (cls.includes('blue') || cls.includes('deepsea') || cls.includes('0466C8')) return 'bg-[#0466C8]'
  return 'bg-muted-foreground'
})
</script>

<template>
  <!-- Primary prominent card -->
  <Card
    v-if="priority === 'primary'"
    class="p-5 transition-all duration-150 hover:-translate-y-0.5 hover:border-border hover:shadow-sm"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="space-y-1">
        <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{{ stat.label }}</p>
        <p class="text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">{{ stat.value }}</p>
      </div>
      <div class="flex size-10 shrink-0 items-center justify-center rounded-xl border border-border/50 bg-muted/60 text-foreground/80 shadow-2xs">
        <Icon class="size-5" aria-hidden="true" />
      </div>
    </div>
    <div class="mt-3.5 flex items-center">
      <span class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold shadow-2xs" :class="pillClass">
        <span class="size-1.5 rounded-full" :class="pillDot" aria-hidden="true" />
        {{ stat.note }}
      </span>
    </div>
  </Card>

  <!-- Secondary compact card -->
  <Card
    v-else
    class="p-4 transition-all duration-150 hover:border-border hover:shadow-xs"
  >
    <div class="flex items-center justify-between gap-2">
      <p class="truncate text-xs font-medium text-muted-foreground" :title="stat.label">{{ stat.label }}</p>
      <div class="flex size-7 shrink-0 items-center justify-center rounded-lg bg-muted/60 text-muted-foreground">
        <Icon class="size-3.5" aria-hidden="true" />
      </div>
    </div>
    <p class="mt-1 text-2xl font-bold tracking-tight text-foreground">{{ stat.value }}</p>
    <p class="mt-1 truncate text-xs font-medium" :class="stat.noteClass" :title="stat.note">
      {{ stat.note }}
    </p>
  </Card>
</template>
