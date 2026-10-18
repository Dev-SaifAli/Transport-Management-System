<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <div :class="cn('flex items-center justify-between gap-4 px-5 pt-5 pb-3', props.class)">
    <slot />
  </div>
</template>
