<script setup lang="ts">
import { computed } from 'vue'

import StatCard from '@/components/shared/StatCard.vue'
import type { KpiStat } from '@/types/dashboard'

const props = defineProps<{ kpis: KpiStat[] }>()

const PRIMARY_IDS = ['todays-trips', 'unassigned-trips', 'active-now', 'trucks-available']

const primaryKpis = computed(() => {
  const map = new Map(props.kpis.map((k) => [k.id, k]))
  const items: KpiStat[] = []
  for (const id of PRIMARY_IDS) {
    const found = map.get(id)
    if (found) items.push(found)
  }
  return items.length > 0 ? items : props.kpis.slice(0, 4)
})

const secondaryKpis = computed(() => {
  return props.kpis.filter((k) => !PRIMARY_IDS.includes(k.id))
})
</script>

<template>
  <div class="space-y-3.5">
    <!-- Primary operational focus tier -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard v-for="stat in primaryKpis" :key="stat.id" :stat="stat" priority="primary" />
    </div>

    <!-- Secondary operational support tier -->
    <div v-if="secondaryKpis.length > 0" class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatCard v-for="stat in secondaryKpis" :key="stat.id" :stat="stat" priority="secondary" />
    </div>
  </div>
</template>
