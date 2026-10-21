<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { PendingAssignment } from '@/types/dashboard'

defineProps<{ items: PendingAssignment[] }>()
</script>

<template>
  <Card>
    <CardHeader class="flex items-center justify-between border-b border-border/70 pb-3">
      <CardTitle class="text-base font-bold tracking-tight text-foreground">Pending Assignments</CardTitle>
      <Badge variant="amber" class="size-6 justify-center rounded-full p-0 font-mono text-xs font-bold">{{ items.length }}</Badge>
    </CardHeader>
    <CardContent class="divide-y divide-border/60 p-0">
      <div v-if="items.length === 0" class="py-8 text-center">
        <p class="text-xs font-medium text-muted-foreground">All trips assigned. No pending queue.</p>
      </div>

      <div
        v-for="item in items"
        :key="item.id"
        class="flex items-center justify-between gap-3 px-5 py-3.5 transition-colors hover:bg-muted/40"
      >
        <div class="min-w-0 flex-1">
          <p class="font-mono text-sm font-bold tracking-tight text-foreground">{{ item.id }}</p>
          <p
            class="mt-0.5 truncate text-xs text-muted-foreground"
            :title="`${item.material} · ${item.origin} → ${item.destination}`"
          >
            {{ item.material }} · {{ item.origin }} → {{ item.destination }}
          </p>
          <p class="mt-0.5 text-[11px] font-medium text-muted-foreground/80">{{ item.scheduleLabel }}</p>
        </div>
        <RouterLink
          to="/dispatch-board"
          class="shrink-0 rounded-full bg-[#001845] px-3.5 py-1 text-xs font-semibold text-white shadow-xs transition-all hover:bg-[#002855] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Assign
        </RouterLink>
      </div>
    </CardContent>
  </Card>
</template>
