<script setup lang="ts">
import StatCard from '@/components/shared/StatCard.vue'
import type { KpiStat } from '@/types/dashboard'

defineProps<{ kpis: KpiStat[] }>()
</script>

<template>
  <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
    <StatCard v-for="stat in kpis" :key="stat.id" :stat="stat" />
  </div>
</template>
