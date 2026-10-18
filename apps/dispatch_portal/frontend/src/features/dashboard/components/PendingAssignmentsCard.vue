<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { PendingAssignment } from '@/types/dashboard'

defineProps<{ items: PendingAssignment[] }>()
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Pending Assignments</CardTitle>
      <Badge variant="amber" class="size-6 justify-center rounded-full p-0 text-xs">{{ items.length }}</Badge>
    </CardHeader>
    <CardContent class="space-y-1">
      <div
        v-for="(item, index) in items"
        :key="item.id"
        class="flex items-center justify-between gap-3 rounded-xl px-3 py-3"
        :class="{ 'border-t': index > 0 }"
      >
        <div class="min-w-0">
          <p class="text-sm font-bold tracking-tight">{{ item.id }}</p>
          <p class="mt-0.5 truncate text-[13px] text-muted-foreground">
            {{ item.material }} · {{ item.origin }} → {{ item.destination }}
          </p>
          <p class="mt-0.5 text-xs text-muted-foreground">{{ item.scheduleLabel }}</p>
        </div>
        <RouterLink
          to="/dispatch-board"
          class="shrink-0 rounded-lg bg-lime-100 px-3.5 py-1.5 text-xs font-bold text-lime-800 transition-colors hover:bg-lime-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Assign
        </RouterLink>
      </div>
    </CardContent>
  </Card>
</template>
