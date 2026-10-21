<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

interface Props {
  title: string
  subtitle?: string
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <div :class="cn('mb-6 flex flex-wrap items-center justify-between gap-4', props.class)">
    <div class="space-y-1">
      <h1 class="text-2xl font-bold tracking-tight text-foreground sm:text-[26px]">{{ props.title }}</h1>
      <p v-if="props.subtitle" class="text-xs font-medium text-muted-foreground">{{ props.subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2.5">
      <slot name="actions" />
    </div>
  </div>
</template>
