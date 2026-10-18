<script setup lang="ts">
import { AvatarFallback, type AvatarFallbackProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

const props = defineProps<AvatarFallbackProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <AvatarFallback
    v-bind="props"
    :class="cn('flex size-full items-center justify-center rounded-full bg-primary/30 text-sm font-bold', props.class)"
  >
    <slot />
  </AvatarFallback>
</template>
