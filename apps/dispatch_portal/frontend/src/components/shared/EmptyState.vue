<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'

interface Props {
  title?: string
  description?: string
}

withDefaults(defineProps<Props>(), {
  title: 'Nothing here yet',
  description: 'There is no data to display at the moment.',
})
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 py-12 text-center">
    <div class="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
      <Inbox class="size-5" aria-hidden="true" />
    </div>
    <p class="text-sm font-semibold">{{ title }}</p>
    <p class="max-w-xs text-sm text-muted-foreground">{{ description }}</p>
    <slot />
  </div>
</template>
