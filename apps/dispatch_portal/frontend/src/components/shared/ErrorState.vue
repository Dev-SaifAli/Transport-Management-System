<script setup lang="ts">
import { TriangleAlert } from 'lucide-vue-next'

import { Button } from '@/components/ui/button'

interface Props {
  title?: string
  description?: string
}

withDefaults(defineProps<Props>(), {
  title: 'Something went wrong',
  description: 'The data could not be loaded. Please try again.',
})

const emit = defineEmits<{ (e: 'retry'): void }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-12 text-center">
    <div class="flex size-11 items-center justify-center rounded-full bg-red-100 text-red-600">
      <TriangleAlert class="size-5" aria-hidden="true" />
    </div>
    <p class="text-sm font-semibold">{{ title }}</p>
    <p class="max-w-sm text-sm text-muted-foreground">{{ description }}</p>
    <Button variant="outline" size="sm" class="mt-1" @click="emit('retry')">Try again</Button>
  </div>
</template>
