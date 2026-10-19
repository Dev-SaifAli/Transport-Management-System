<script setup lang="ts">
import { Plus, UserPlus } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/shared/LoadingState.vue'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { useDashboardStore } from '@/stores/dashboard'

import AwaitingVerificationCard from './components/AwaitingVerificationCard.vue'
import LiveFleetMapCard from './components/LiveFleetMapCard.vue'
import PendingAssignmentsCard from './components/PendingAssignmentsCard.vue'
import RecentActivityCard from './components/RecentActivityCard.vue'
import StatGrid from './components/StatGrid.vue'
import TodayDispatchCard from './components/TodayDispatchCard.vue'

const router = useRouter()
const store = useDashboardStore()

const overview = computed(() => store.overview)

const todayLabel = new Intl.DateTimeFormat('en-GB', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
}).format(new Date())

const subtitle = computed(() => `${todayLabel} · Live dispatch overview for AL RANA TRANSPORT LLC`)
</script>

<template>
  <PageContainer>
    <PageHeader title="Operations Dashboard" :subtitle="subtitle">
      <template #actions>
        <Button size="lg" class="rounded-lg" @click="router.push('/create-trip')">
          <Plus aria-hidden="true" />
          Create Trip
        </Button>
        <Button size="lg" variant="outline" class="rounded-lg" @click="router.push('/dispatch-board')">
          <UserPlus aria-hidden="true" />
          Assign Truck &amp; Driver
        </Button>
      </template>
    </PageHeader>

    <LoadingState v-if="store.status === 'loading' || store.status === 'idle'" label="Loading dispatch overview…" />

    <template v-else-if="store.status === 'success' && overview">
      <StatGrid :kpis="overview.kpis" />

      <div class="mt-4 grid grid-cols-12 gap-4">
        <!-- Left column: dispatch list + fleet map -->
        <div class="col-span-12 flex flex-col gap-4 xl:col-span-5">
          <TodayDispatchCard :trips="overview.todaysDispatch" />
          <LiveFleetMapCard :markers="overview.fleetMap.markers" />
        </div>

        <!-- Middle column: assignments + verification -->
        <div class="col-span-12 flex flex-col gap-4 xl:col-span-4">
          <PendingAssignmentsCard :items="overview.pendingAssignments" />
          <AwaitingVerificationCard :items="overview.awaitingVerification" />
        </div>

        <!-- Right column: activity feed -->
        <div class="col-span-12 xl:col-span-3">
          <RecentActivityCard :items="overview.recentActivity" />
        </div>
      </div>
    </template>

    <div v-else class="rounded-2xl border bg-card shadow-sm">
      <ErrorState :description="store.error ?? undefined" @retry="store.refresh()" />
    </div>
  </PageContainer>
</template>
