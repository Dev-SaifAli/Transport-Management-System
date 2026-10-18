<script setup lang="ts">
import { computed } from 'vue'

import { Badge } from '@/components/ui/badge'
import type { BoardColumnKey } from '@/types/board'
import type { TripStatus } from '@/types/dashboard'

type Status = TripStatus | BoardColumnKey

type StatusConfig = {
  label: string
  variant: 'blue' | 'amber' | 'green' | 'red'
  dot: string
}

const statusConfig: Record<Status, StatusConfig> = {
  unassigned: { label: 'Unassigned', variant: 'red', dot: 'bg-red-600' },
  'in-transit': { label: 'In Transit', variant: 'blue', dot: 'bg-blue-600' },
  loading: { label: 'Loading', variant: 'amber', dot: 'bg-amber-600' },
  scheduled: { label: 'Scheduled', variant: 'blue', dot: 'bg-blue-600' },
  delivered: { label: 'Delivered', variant: 'green', dot: 'bg-emerald-600' },
  'awaiting-verification': { label: 'Awaiting Verification', variant: 'amber', dot: 'bg-amber-600' },
  completed: { label: 'Completed', variant: 'green', dot: 'bg-emerald-600' },
  pending: { label: 'Pending', variant: 'amber', dot: 'bg-amber-600' },
  correction: { label: 'Correction', variant: 'red', dot: 'bg-red-600' },
  attention: { label: 'Needs Attention', variant: 'red', dot: 'bg-red-600' },
}

const props = defineProps<{ status: Status }>()

const config = computed(() => statusConfig[props.status])
</script>

<template>
  <Badge :variant="config.variant">
    <span v-if="config.dot" class="size-1.5 rounded-full" :class="config.dot" aria-hidden="true" />
    {{ config.label }}
  </Badge>
</template>
