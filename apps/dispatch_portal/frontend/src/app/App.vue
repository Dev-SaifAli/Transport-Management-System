<script setup lang="ts">
import { onMounted } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { useDashboardStore } from '@/stores/dashboard'

const dashboardStore = useDashboardStore()

onMounted(() => {
  void dashboardStore.fetchOverview()
})
</script>

<template>
  <AppShell @refresh="dashboardStore.refresh()">
    <RouterView />
  </AppShell>
</template>
