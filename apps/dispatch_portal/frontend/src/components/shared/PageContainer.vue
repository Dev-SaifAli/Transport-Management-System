<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <main :class="cn('flex-1 px-4 py-6 sm:px-6 lg:px-8', props.class)">
    <slot />
  </main>
</template>
