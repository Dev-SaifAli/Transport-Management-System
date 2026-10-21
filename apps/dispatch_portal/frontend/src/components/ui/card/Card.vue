<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <div :class="cn('rounded-2xl border border-border/80 bg-card text-card-foreground shadow-[0_2px_12px_rgba(0,0,0,0.025)] transition-all', props.class)">
    <slot />
  </div>
</template>
