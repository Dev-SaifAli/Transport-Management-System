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

const props = defineProps<{ stat: KpiStat }>()

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
</script>

<template>
  <Card class="p-5">
    <div class="flex items-start justify-between gap-4">
      <div class="space-y-1.5">
        <p class="text-sm font-medium text-muted-foreground">{{ stat.label }}</p>
        <p class="text-3xl font-extrabold tracking-tight">{{ stat.value }}</p>
      </div>
      <div class="flex size-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Icon class="size-[18px]" aria-hidden="true" />
      </div>
    </div>
    <p class="mt-3 text-[13px] font-medium" :class="stat.noteClass">{{ stat.note }}</p>
  </Card>
</template>
