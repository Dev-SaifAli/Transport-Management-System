<script setup lang="ts">
interface Props {
  label?: string
}

withDefaults(defineProps<Props>(), { label: 'Loading…' })
</script>

<template>
  <div class="flex items-center justify-center gap-3 py-12 text-muted-foreground" role="status" aria-live="polite">
    <svg class="size-5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.4 0 0 5.4 0 12h4Z" />
    </svg>
    <span class="text-sm font-medium">{{ label }}</span>
  </div>
</template>
