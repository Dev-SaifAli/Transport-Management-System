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
    <CardHeader class="border-b border-border/70 pb-3">
      <CardTitle class="text-base font-bold tracking-tight text-foreground">Recent Activity</CardTitle>
    </CardHeader>
    <CardContent class="px-5 py-5">
      <div v-if="props.items.length === 0" class="py-8 text-center">
        <p class="text-xs font-medium text-muted-foreground">No recent dispatch activity recorded.</p>
      </div>

      <ol v-else class="relative space-y-5">
        <span class="absolute bottom-3 left-4 top-3 w-px bg-border/80" aria-hidden="true" />
        <li v-for="(item, index) in props.items" :key="index" class="relative flex items-start gap-3.5">
          <div
            class="relative z-10 flex size-8 shrink-0 items-center justify-center rounded-full border border-border/80 bg-card text-foreground ring-4 ring-card shadow-2xs"
            :class="item.iconClass"
          >
            <component :is="iconFor(item)" class="size-3.5" aria-hidden="true" />
          </div>
          <div class="min-w-0 pt-0.5">
            <p class="flex flex-wrap items-baseline gap-x-2">
              <span class="font-mono text-xs font-bold text-foreground">{{ item.ref }}</span>
              <time class="text-[11px] font-medium tabular-nums text-muted-foreground">{{ item.time }}</time>
            </p>
            <p class="mt-0.5 text-xs font-normal leading-relaxed text-muted-foreground">{{ item.description }}</p>
          </div>
        </li>
      </ol>
    </CardContent>
  </Card>
</template>
