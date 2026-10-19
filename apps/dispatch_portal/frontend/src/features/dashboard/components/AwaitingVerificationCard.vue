<script setup lang="ts">
import { Upload } from 'lucide-vue-next'

import StatusBadge from '@/components/shared/StatusBadge.vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { VerificationItem } from '@/types/dashboard'

defineProps<{ items: VerificationItem[] }>()
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Awaiting Verification</CardTitle>
    </CardHeader>
    <CardContent class="space-y-1">
      <div
        v-for="(item, index) in items"
        :key="`${item.id}-${index}`"
        class="flex items-center justify-between gap-3 rounded-xl px-3 py-3"
        :class="{ 'border-t': index > 0 }"
      >
        <div class="flex min-w-0 items-start gap-3">
          <div class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
            <Upload class="size-4" aria-hidden="true" />
          </div>
          <div class="min-w-0">
            <p class="text-sm font-bold tracking-tight">{{ item.id }}</p>
            <p class="mt-0.5 truncate text-[13px] text-muted-foreground">{{ item.description }}</p>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ item.meta }}</p>
          </div>
        </div>
        <StatusBadge :status="item.status" class="shrink-0" />
      </div>
    </CardContent>
  </Card>
</template>
