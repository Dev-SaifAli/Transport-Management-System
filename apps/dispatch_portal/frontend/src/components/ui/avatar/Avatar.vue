<script setup lang="ts">
import { AvatarRoot, type AvatarRootProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

const props = defineProps<AvatarRootProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <AvatarRoot
    v-bind="props"
    :class="cn('relative flex size-10 shrink-0 overflow-hidden rounded-full', props.class)"
  >
    <slot />
  </AvatarRoot>
</template>
