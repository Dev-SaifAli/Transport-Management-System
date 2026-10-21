<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { AlertCircle, Plus, Truck, UserPlus, Users } from 'lucide-vue-next'

import ErrorState from '@/components/shared/ErrorState.vue'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import { Button } from '@/components/ui/button'
import { useDashboardStore } from '@/stores/dashboard'

import AwaitingVerificationCard from './components/AwaitingVerificationCard.vue'
import DispatchCommandList from './components/DispatchCommandList.vue'
import KpiBentoCard from './components/KpiBentoCard.vue'
import LiveFleetMapCard from './components/LiveFleetMapCard.vue'
import PendingAssignmentsCard from './components/PendingAssignmentsCard.vue'
import RecentActivityCard from './components/RecentActivityCard.vue'
import SecondaryMetricsRibbon from './components/SecondaryMetricsRibbon.vue'

const router = useRouter()
const store = useDashboardStore()

const todayLabel = new Intl.DateTimeFormat('en-GB', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
}).format(new Date())

const subtitle = computed(() => `${todayLabel} · Live Operations & Fleet Telemetry`)

const isInitialLoading = computed(() => store.status === 'loading' && !store.overview)

// Fleet utilization progress calculation
const fleetUtilizationPercent = computed(() => {
  const totalFleet = store.trucksAvailable + store.activeNow
  if (totalFleet === 0) return 72
  return Math.round((store.activeNow / totalFleet) * 100)
})

onMounted(() => {
  if (store.status === 'idle') {
    void store.fetchDashboardData()
  }
})
</script>

<template>
  <PageContainer>
    <!-- Header with Quick Action Buttons -->
    <PageHeader title="Operations Dashboard" :subtitle="subtitle">
      <template #actions>
        <Button
          class="h-10 rounded-full border-0 bg-[#0466C8] px-5 text-sm font-bold text-white shadow-sm transition-all hover:bg-[#0353A4] focus-visible:ring-2 focus-visible:ring-[#0466C8]/50 cursor-pointer"
          @click="router.push('/create-trip')"
        >
          <Plus class="size-4 text-white" aria-hidden="true" />
          Create Trip
        </Button>
        <Button
          variant="outline"
          class="h-10 rounded-full border-border/80 bg-card px-4 text-sm font-semibold text-foreground shadow-xs transition-all hover:bg-muted/70 cursor-pointer"
          @click="router.push('/dispatch-board')"
        >
          <UserPlus class="size-4 text-muted-foreground" aria-hidden="true" />
          Assign Truck &amp; Driver
        </Button>
      </template>
    </PageHeader>

    <!-- Error State -->
    <div v-if="store.status === 'error' && !store.overview" class="rounded-2xl border border-border/80 bg-card shadow-sm p-6">
      <ErrorState :description="store.error ?? undefined" @retry="store.refresh()" />
    </div>

    <!-- Main Dashboard Content with Cascading Animations -->
    <div v-else class="space-y-6">
      <!-- 1. Top Bento KPI Grid (4 Columns) -->
      <section aria-label="Key Performance Indicators">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <!-- Card 1: Today's Trips (Sparkline) -->
          <KpiBentoCard
            title="Today's Trips"
            :value="store.todaysTrips"
            :subtext="`${store.scheduled} scheduled today`"
            badge-color="blue"
            visual-type="sparkline"
            :loading="isInitialLoading"
            :icon="Users"
          />

          <!-- Card 2: Unassigned Trips (Segmented Bar) -->
          <KpiBentoCard
            title="Unassigned Trips"
            :value="store.unassignedTrips"
            :subtext="store.unassignedTrips > 0 ? 'Awaiting truck & driver' : 'All assigned'"
            :badge-color="store.unassignedTrips > 0 ? 'amber' : 'emerald'"
            visual-type="segmented"
            :segmented-values="[
              { label: 'Assigned', count: Math.max(store.todaysTrips - store.unassignedTrips, 1), colorClass: 'bg-[#0466C8]' },
              { label: 'Unassigned', count: store.unassignedTrips, colorClass: 'bg-amber-500' },
            ]"
            :loading="isInitialLoading"
            :icon="AlertCircle"
          />

          <!-- Card 3: Active Now (Live Meter) -->
          <KpiBentoCard
            title="Active Now"
            :value="store.activeNow"
            :subtext="`${store.activeNow} in transit / loading`"
            badge-color="blue"
            visual-type="meter"
            :loading="isInitialLoading"
            :icon="Truck"
          />

          <!-- Card 4: Trucks Available (Progress Bar) -->
          <KpiBentoCard
            title="Trucks Available"
            :value="store.trucksAvailable"
            subtext="Idle own fleet"
            badge-color="emerald"
            visual-type="progress"
            :visual-progress="fleetUtilizationPercent"
            :loading="isInitialLoading"
            :icon="Truck"
          />
        </div>
      </section>

      <!-- 2. Full-Width Secondary Metrics Ribbon -->
      <section aria-label="Secondary Metrics">
        <SecondaryMetricsRibbon
          :scheduled="store.scheduled"
          :completed="store.completed"
          :need-attention="store.needAttention"
          :drivers-available="store.driversAvailable"
          :loading="isInitialLoading"
        />
      </section>

      <!-- 3. Hero Operations Row: Today's Dispatch (8 cols) + Live Fleet Telemetry Map (4 cols) -->
      <section aria-label="Live Operations">
        <div class="grid grid-cols-12 items-stretch gap-5">
          <div class="col-span-12 flex flex-col xl:col-span-8">
            <DispatchCommandList
              :trips="store.todaysDispatch"
              :loading="isInitialLoading"
            />
          </div>

          <div class="col-span-12 flex flex-col xl:col-span-4">
            <LiveFleetMapCard
              :markers="store.fleetMarkers"
              :loading="isInitialLoading"
            />
          </div>
        </div>
      </section>

      <!-- 4. Action Queues & Activity Feed (3 Columns) -->
      <section aria-label="Action Queues and Activity">
        <div class="grid grid-cols-12 gap-5">
          <div class="col-span-12 md:col-span-6 xl:col-span-4">
            <PendingAssignmentsCard :items="store.pendingAssignments" />
          </div>
          <div class="col-span-12 md:col-span-6 xl:col-span-4">
            <AwaitingVerificationCard :items="store.awaitingVerification" />
          </div>
          <div class="col-span-12 md:col-span-12 xl:col-span-4">
            <RecentActivityCard :items="store.recentActivity" />
          </div>
        </div>
      </section>
    </div>
  </PageContainer>
</template>
