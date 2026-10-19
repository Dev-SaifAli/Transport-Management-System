<script setup lang="ts">
import { onMounted } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useDispatchBoardStore } from '@/stores/dispatchBoard'
import { useDispatchTableStore } from '@/stores/dispatchTable'
import { useQuotationsStore } from '@/stores/quotations'

const dashboardStore = useDashboardStore()
const boardStore = useDispatchBoardStore()
const tableStore = useDispatchTableStore()
const quotationsStore = useQuotationsStore()

function handleRefresh() {
  void dashboardStore.refresh()
  if (boardStore.status !== 'idle') void boardStore.fetchBoard()
  if (tableStore.status !== 'idle') void tableStore.fetchTrips()
  if (quotationsStore.status !== 'idle') void quotationsStore.fetchQuotations()
}

onMounted(() => {
  void dashboardStore.fetchOverview()
})
</script>

<template>
  <AppShell @refresh="handleRefresh">
    <RouterView />
  </AppShell>
</template>
