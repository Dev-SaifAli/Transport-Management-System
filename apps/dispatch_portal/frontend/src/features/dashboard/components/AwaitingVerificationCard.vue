<script setup lang="ts">
import { Upload } from 'lucide-vue-next'

import StatusBadge from '@/components/shared/StatusBadge.vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { VerificationItem } from '@/types/dashboard'

defineProps<{ items: VerificationItem[] }>()
</script>

<template>
  <Card>
    <CardHeader class="border-b border-border/70 pb-3">
      <CardTitle class="text-base font-bold tracking-tight text-foreground">Awaiting Verification</CardTitle>
    </CardHeader>
    <CardContent class="divide-y divide-border/60 p-0">
      <div v-if="items.length === 0" class="py-8 text-center">
        <p class="text-xs font-medium text-muted-foreground">No documents awaiting verification review.</p>
      </div>

      <div
        v-for="(item, index) in items"
        :key="`${item.id}-${index}`"
        class="flex items-center justify-between gap-3 px-5 py-3.5 transition-colors hover:bg-muted/40"
      >
        <div class="flex min-w-0 items-center gap-3">
          <div class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border/70 bg-muted/60 text-muted-foreground">
            <Upload class="size-3.5" aria-hidden="true" />
          </div>
          <div class="min-w-0">
            <p class="font-mono text-sm font-bold tracking-tight text-foreground">{{ item.id }}</p>
            <p class="mt-0.5 truncate text-xs text-muted-foreground" :title="item.description">{{ item.description }}</p>
            <p class="mt-0.5 text-[11px] font-medium text-muted-foreground/80">{{ item.meta }}</p>
          </div>
        </div>
        <StatusBadge :status="item.status" class="shrink-0" />
      </div>
    </CardContent>
  </Card>
</template>
