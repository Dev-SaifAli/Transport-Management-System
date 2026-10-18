<script setup lang="ts">
import { Check, FolderOpen, Package, ShieldCheck, Truck, UserCheck, type LucideIcon } from 'lucide-vue-next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ActivityItem } from '@/types/dashboard'

const props = defineProps<{ items: ActivityItem[] }>()

const iconMap: Record<string, LucideIcon> = {
  folder: FolderOpen,
  package: Package,
  check: Check,
  shield: ShieldCheck,
  truck: Truck,
  'user-check': UserCheck,
}

function iconFor(item: ActivityItem): LucideIcon {
  return iconMap[item.icon] ?? Package
}
</script>

<template>
  <Card class="h-full">
    <CardHeader>
      <CardTitle>Recent Activity</CardTitle>
    </CardHeader>
    <CardContent>
      <ol class="relative space-y-5">
        <span class="absolute bottom-3 left-[17px] top-3 w-px bg-border" aria-hidden="true" />
        <li v-for="(item, index) in props.items" :key="index" class="relative flex items-start gap-3">
          <div
            class="relative z-10 flex size-9 shrink-0 items-center justify-center rounded-lg ring-4 ring-card"
            :class="item.iconClass"
          >
            <component :is="iconFor(item)" class="size-4" aria-hidden="true" />
          </div>
          <div class="min-w-0 pt-0.5">
            <p class="flex flex-wrap items-baseline gap-x-2">
              <span class="text-[13px] font-bold text-lime-700">{{ item.ref }}</span>
              <time class="text-xs text-muted-foreground">{{ item.time }}</time>
            </p>
            <p class="mt-0.5 text-[13px] font-medium leading-snug">{{ item.description }}</p>
          </div>
        </li>
      </ol>
    </CardContent>
  </Card>
</template>
