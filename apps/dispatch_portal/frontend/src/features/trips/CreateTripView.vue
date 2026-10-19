<script setup lang="ts">
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  Layers,
  MapPin,
  RefreshCw,
  Send,
  Truck,
  UserCheck,
} from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { createTripsService } from '@/services/api/trips'
import type {
  CreateTripRequest,
  CreateTripResponse,
  FleetResourceOptions,
  RouteOptionsResponse,
  TransportJobOption,
} from '@/types/trips'

const route = useRoute()
const router = useRouter()
const api = createTripsService()

const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const successTrip = ref<CreateTripResponse | null>(null)

const jobs = ref<TransportJobOption[]>([])
const selectedJobName = ref('')
const routeOptions = ref<RouteOptionsResponse | null>(null)
const fleet = ref<FleetResourceOptions>({
  trucks: [],
  drivers: [],
  transporters: [],
  hiredVehicles: [],
})

const tripDate = ref(new Date().toISOString().slice(0, 10))
const loadingSite = ref('')
const unloadingSite = ref('')
const plannedQuantity = ref<number | undefined>(undefined)
const executionSource = ref<'OWN' | 'HIRED'>('OWN')
const vehicle = ref('')
const driver = ref('')
const transporter = ref('')
const hiredVehicle = ref('')
const hiredDriver = ref('')

const selectedJob = computed(() => jobs.value.find((j) => j.name === selectedJobName.value) || null)
const isOpenQuantityJob = computed(() => selectedJob.value?.quantity_mode === 'Open')

const availableLoadingPoints = computed(() => routeOptions.value?.loading_points || [])
const availableDestinations = computed(() => {
  if (!routeOptions.value) return []
  if (!isOpenQuantityJob.value) return routeOptions.value.destinations
  if (!loadingSite.value) return routeOptions.value.destinations
  const validForLoading = routeOptions.value.routes
    .filter((r) => r.loading_location === loadingSite.value)
    .map((r) => r.unloading_location)
  return [...new Set(validForLoading)]
})

const isRouteAuthorized = computed(() => {
  if (!loadingSite.value || !unloadingSite.value) return false
  if (!isOpenQuantityJob.value) return true
  if (!routeOptions.value?.routes) return false
  return routeOptions.value.routes.some(
    (r) => r.loading_location === loadingSite.value && r.unloading_location === unloadingSite.value,
  )
})

const availableHiredVehicles = computed(() => {
  if (!transporter.value) return fleet.value.hiredVehicles
  return fleet.value.hiredVehicles.filter((hv) => hv.transporter === transporter.value)
})

const canSubmit = computed(() => {
  if (!selectedJobName.value) return false
  if (!loadingSite.value || !unloadingSite.value) return false
  if (isOpenQuantityJob.value && !isRouteAuthorized.value) return false
  if (!isOpenQuantityJob.value && (!plannedQuantity.value || Number(plannedQuantity.value) <= 0)) return false
  if (!tripDate.value) return false
  if (executionSource.value === 'OWN') {
    if (!driver.value) return false
  } else {
    if (!transporter.value || !hiredVehicle.value) return false
  }
  return true
})

onMounted(async () => {
  try {
    loading.value = true
    error.value = ''
    const [fetchedJobs, fetchedFleet] = await Promise.all([
      api.getJobs(),
      api.getFleetResources(),
    ])
    jobs.value = fetchedJobs
    fleet.value = fetchedFleet

    const jobFromQuery = (route.query.transport_job as string) || (route.query.job as string)
    if (jobFromQuery && jobs.value.some((j) => j.name === jobFromQuery)) {
      selectedJobName.value = jobFromQuery
    } else if (jobs.value.length > 0) {
      selectedJobName.value = jobs.value[0].name
    }
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to initialize trip form.'
  } finally {
    loading.value = false
  }
})

watch(selectedJobName, async (newJob) => {
  if (!newJob) {
    routeOptions.value = null
    loadingSite.value = ''
    unloadingSite.value = ''
    return
  }
  try {
    error.value = ''
    const opts = await api.getRouteOptions(newJob)
    routeOptions.value = opts

    // Set initial loading site
    if (opts.loading_points.length === 1) {
      loadingSite.value = opts.loading_points[0]
    } else if (selectedJob.value?.loading_site && opts.loading_points.includes(selectedJob.value.loading_site)) {
      loadingSite.value = selectedJob.value.loading_site
    } else if (opts.loading_points.length > 0) {
      loadingSite.value = opts.loading_points[0]
    } else {
      loadingSite.value = ''
    }

    // Set initial destination
    const validDests = opts.routes
      .filter((r) => r.loading_location === loadingSite.value)
      .map((r) => r.unloading_location)
    if (validDests.length === 1) {
      unloadingSite.value = validDests[0]
    } else if (selectedJob.value?.unloading_site && validDests.includes(selectedJob.value.unloading_site)) {
      unloadingSite.value = selectedJob.value.unloading_site
    } else if (validDests.length > 0) {
      unloadingSite.value = validDests[0]
    } else {
      unloadingSite.value = ''
    }

    if (selectedJob.value?.requested_date) {
      tripDate.value = selectedJob.value.requested_date
    }
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load route options for selected job.'
  }
})

watch(loadingSite, (newLoading) => {
  if (!newLoading || !routeOptions.value) return
  const validDests = routeOptions.value.routes
    .filter((r) => r.loading_location === newLoading)
    .map((r) => r.unloading_location)
  if (!validDests.includes(unloadingSite.value)) {
    unloadingSite.value = validDests.length ? validDests[0] : ''
  }
})

async function submitTrip() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  error.value = ''
  successTrip.value = null

  try {
    const payload: CreateTripRequest = {
      transport_job: selectedJobName.value,
      trip_date: tripDate.value,
      execution_source: executionSource.value,
      material: selectedJob.value?.material || '',
      loading_site: loadingSite.value,
      unloading_site: unloadingSite.value,
      planned_quantity: plannedQuantity.value ? Number(plannedQuantity.value) : 0,
      vehicle: executionSource.value === 'OWN' ? vehicle.value || undefined : undefined,
      driver: executionSource.value === 'OWN' ? driver.value || undefined : undefined,
      transporter: executionSource.value === 'HIRED' ? transporter.value || undefined : undefined,
      hired_vehicle: executionSource.value === 'HIRED' ? hiredVehicle.value || undefined : undefined,
      hired_driver: executionSource.value === 'HIRED' ? hiredDriver.value || undefined : undefined,
    }

    const res = await api.createTrip(payload)
    successTrip.value = res
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to create transport trip.'
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  successTrip.value = null
  vehicle.value = ''
  driver.value = ''
  transporter.value = ''
  hiredVehicle.value = ''
  hiredDriver.value = ''
  plannedQuantity.value = undefined
}
</script>

<template>
  <PageContainer>
    <PageHeader
      title="Create Transport Trip"
      subtitle="Dispatch a new trip with authorized route validation and assignment"
    >
      <template #actions>
        <Button variant="outline" size="sm" @click="router.push('/dispatch-board')">
          <ArrowLeft class="mr-2 h-4 w-4" />
          Dispatch Board
        </Button>
      </template>
    </PageHeader>

    <div v-if="loading" class="flex items-center justify-center py-20 text-muted-foreground">
      <RefreshCw class="mr-2 h-5 w-5 animate-spin" />
      Loading dispatch details...
    </div>

    <div v-else class="space-y-6 max-w-4xl">
      <!-- Error Alert -->
      <div
        v-if="error"
        class="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"
      >
        <AlertCircle class="h-5 w-5 shrink-0 text-red-600 mt-0.5" />
        <div class="flex-1 font-medium">{{ error }}</div>
      </div>

      <!-- Success Card -->
      <div
        v-if="successTrip"
        class="rounded-xl border border-green-200 bg-green-50/70 p-6 shadow-sm"
      >
        <div class="flex items-start gap-4">
          <div class="rounded-full bg-green-100 p-2 text-green-700">
            <CheckCircle2 class="h-6 w-6" />
          </div>
          <div class="flex-1 space-y-2">
            <h3 class="text-lg font-bold text-green-950">
              Transport Trip Created Successfully: {{ successTrip.name }}
            </h3>
            <p class="text-sm text-green-800">
              Trip assigned to Transport Job <span class="font-semibold">{{ successTrip.transport_job }}</span>.
              Commercial rate snapshot will automatically lock upon verified loading.
            </p>
            <div class="flex items-center gap-3 pt-2">
              <Button size="sm" class="bg-green-700 hover:bg-green-800 text-white" @click="router.push('/dispatch-board')">
                View on Dispatch Board
              </Button>
              <Button size="sm" variant="outline" @click="resetForm">
                Create Another Trip
              </Button>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Form -->
      <form v-if="!successTrip" class="space-y-6" @submit.prevent="submitTrip">
        <!-- 1. Select Transport Job -->
        <div class="rounded-xl border bg-card p-6 shadow-sm space-y-4">
          <div class="flex items-center justify-between border-b pb-3">
            <h2 class="text-base font-semibold flex items-center gap-2">
              <Layers class="h-4 w-4 text-blue-600" />
              1. Transport Job Selection
            </h2>
            <Badge v-if="selectedJob" :variant="isOpenQuantityJob ? 'default' : 'secondary'">
              {{ isOpenQuantityJob ? 'Open Quantity Mode' : 'Fixed Quantity' }}
            </Badge>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">Select Job</label>
              <select
                v-model="selectedJobName"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="" disabled>-- Choose an active Transport Job --</option>
                <option v-for="job in jobs" :key="job.name" :value="job.name">
                  {{ job.name }} &middot; {{ job.material }} ({{ job.customer || 'No customer' }})
                </option>
              </select>
            </div>

            <div v-if="selectedJob" class="rounded-lg bg-muted/50 p-3 text-xs space-y-1">
              <div><span class="text-muted-foreground">Customer:</span> <strong class="text-foreground">{{ selectedJob.customer || '—' }}</strong></div>
              <div><span class="text-muted-foreground">Material:</span> <strong class="text-foreground">{{ selectedJob.material }}</strong></div>
              <div><span class="text-muted-foreground">Quantity Rule:</span> <span class="font-medium text-foreground">{{ isOpenQuantityJob ? 'Quotation Snapshot (Ton-based, variable trips)' : 'Fixed Order Quantity' }}</span></div>
            </div>
          </div>
        </div>

        <!-- 2. Route Selection & Validation -->
        <div class="rounded-xl border bg-card p-6 shadow-sm space-y-4">
          <div class="flex items-center justify-between border-b pb-3">
            <h2 class="text-base font-semibold flex items-center gap-2">
              <MapPin class="h-4 w-4 text-emerald-600" />
              2. Route Selection & Route Pair Authorization
            </h2>
            <div v-if="loadingSite && unloadingSite">
              <span
                v-if="isRouteAuthorized"
                class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 border border-emerald-200"
              >
                <CheckCircle2 class="h-3.5 w-3.5" />
                Authorized Route Pair
              </span>
              <span
                v-else
                class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 border border-amber-200"
              >
                <AlertCircle class="h-3.5 w-3.5" />
                Unauthorized Route Pair
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">
                Loading Point (Permitted)
              </label>
              <select
                v-model="loadingSite"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="" disabled>-- Select Loading Point --</option>
                <option v-for="pt in availableLoadingPoints" :key="pt" :value="pt">
                  {{ pt }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">
                Destination (Permitted)
              </label>
              <select
                v-model="unloadingSite"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                :disabled="!availableDestinations.length"
              >
                <option value="" disabled>-- Select Destination --</option>
                <option v-for="dest in availableDestinations" :key="dest" :value="dest">
                  {{ dest }}
                </option>
              </select>
            </div>
          </div>

          <div v-if="isOpenQuantityJob && routeOptions?.routes?.length" class="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground">
            <span class="font-semibold text-foreground">Authorized Route Combinations for this Job:</span>
            <div class="mt-1 flex flex-wrap gap-2">
              <span
                v-for="(r, idx) in routeOptions.routes"
                :key="idx"
                class="inline-flex items-center rounded bg-background px-2 py-1 text-[11px] font-mono border"
                :class="r.loading_location === loadingSite && r.unloading_location === unloadingSite ? 'border-emerald-500 font-bold text-emerald-700' : ''"
              >
                {{ r.loading_location }} &rarr; {{ r.unloading_location }}
              </span>
            </div>
          </div>
        </div>

        <!-- 3. Planning & Scheduling -->
        <div class="rounded-xl border bg-card p-6 shadow-sm space-y-4">
          <div class="flex items-center justify-between border-b pb-3">
            <h2 class="text-base font-semibold flex items-center gap-2">
              <Calendar class="h-4 w-4 text-purple-600" />
              3. Planning Details
            </h2>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">Trip Date</label>
              <input
                v-model="tripDate"
                type="date"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                required
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">
                Planned Quantity (TON)
                <span v-if="isOpenQuantityJob" class="text-xs text-muted-foreground font-normal">(Non-binding planning estimate)</span>
                <span v-else class="text-xs text-red-500 font-normal">*Required</span>
              </label>
              <input
                v-model="plannedQuantity"
                type="number"
                step="0.01"
                min="0"
                placeholder="e.g. 25.00"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
        </div>

        <!-- 4. Execution & Resource Assignment -->
        <div class="rounded-xl border bg-card p-6 shadow-sm space-y-4">
          <div class="flex items-center justify-between border-b pb-3">
            <h2 class="text-base font-semibold flex items-center gap-2">
              <Truck class="h-4 w-4 text-amber-600" />
              4. Execution & Fleet Assignment
            </h2>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="rounded-l-md px-3 py-1.5 text-xs font-semibold border transition"
                :class="executionSource === 'OWN' ? 'bg-primary text-primary-foreground border-primary' : 'bg-muted text-muted-foreground border-input'"
                @click="executionSource = 'OWN'"
              >
                Own Fleet
              </button>
              <button
                type="button"
                class="rounded-r-md px-3 py-1.5 text-xs font-semibold border -ml-2 transition"
                :class="executionSource === 'HIRED' ? 'bg-primary text-primary-foreground border-primary' : 'bg-muted text-muted-foreground border-input'"
                @click="executionSource = 'HIRED'"
              >
                Hired Fleet
              </button>
            </div>
          </div>

          <!-- Own Fleet Fields -->
          <div v-if="executionSource === 'OWN'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">Own Vehicle (Truck)</label>
              <select
                v-model="vehicle"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">-- Select Available Truck --</option>
                <option v-for="trk in fleet.trucks" :key="trk.name" :value="trk.name">
                  {{ trk.name }} {{ trk.capacity ? `(${trk.capacity} TON)` : '' }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">Driver (Active)</label>
              <select
                v-model="driver"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                required
              >
                <option value="">-- Select Active Driver --</option>
                <option v-for="drv in fleet.drivers" :key="drv.name" :value="drv.name">
                  {{ drv.full_name || drv.name }}
                </option>
              </select>
            </div>
          </div>

          <!-- Hired Fleet Fields -->
          <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">Transporter Supplier</label>
              <select
                v-model="transporter"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                required
              >
                <option value="">-- Select Transporter --</option>
                <option v-for="t in fleet.transporters" :key="t.name" :value="t.name">
                  {{ t.supplier_name || t.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">Hired Vehicle</label>
              <select
                v-model="hiredVehicle"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                required
                :disabled="!availableHiredVehicles.length"
              >
                <option value="">-- Select Vehicle --</option>
                <option v-for="hv in availableHiredVehicles" :key="hv.name" :value="hv.name">
                  {{ hv.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium mb-1 text-foreground">Hired Driver Name</label>
              <input
                v-model="hiredDriver"
                type="text"
                placeholder="Driver Name"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
        </div>

        <!-- Submit Actions -->
        <div class="flex items-center justify-end gap-3 pt-2">
          <Button type="button" variant="outline" @click="router.push('/dispatch-board')">
            Cancel
          </Button>
          <Button
            type="submit"
            size="lg"
            :disabled="!canSubmit || submitting"
            class="min-w-44"
          >
            <RefreshCw v-if="submitting" class="mr-2 h-4 w-4 animate-spin" />
            <Send v-else class="mr-2 h-4 w-4" />
            Assign &amp; Dispatch Trip
          </Button>
        </div>
      </form>
    </div>
  </PageContainer>
</template>

