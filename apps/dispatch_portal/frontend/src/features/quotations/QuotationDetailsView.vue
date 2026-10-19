<script setup lang="ts">
import { ArrowLeft, CheckCircle2, FilePlus2, MapPin, Pencil, RefreshCw } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import LoadingState from '@/components/shared/LoadingState.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { createQuotationsService } from '@/services/api/quotations'
import type { QuotationSalesOrderSummaryResponse, TransportQuotationDoc } from '@/types/quotations'

const route = useRoute()
const router = useRouter()
const api = createQuotationsService()
const doc = ref<TransportQuotationDoc | null>(null)
const areaSummary = ref<QuotationSalesOrderSummaryResponse | null>(null)
const error = ref('')
const busy = ref(false)
const convertingArea = ref<string | null>(null)
const message = ref('')
const createdOrder = ref('')

const badge = computed(() =>
  doc.value?.status === 'Approved'
    ? 'green'
    : doc.value?.status === 'Pending Approval'
      ? 'amber'
      : doc.value?.status === 'Rejected' || doc.value?.status === 'Cancelled'
        ? 'red'
        : 'blue'
)
const subtitle = computed(() => doc.value?.customer ? doc.value.customer + ' \u00B7 AED' : 'Quotation details')
const pageTitle = computed(() => doc.value?.name ?? 'Quotation')
const showEditButton = computed(() => doc.value?.status === 'Draft' || doc.value?.status === 'Pending Approval')
const showCreateOrderButton = computed(() =>
  doc.value?.status === 'Approved' && (!areaSummary.value || areaSummary.value.has_unconverted_areas)
)

async function load() {
  error.value = ''
  const id = route.params.id as string
  doc.value = await api.getQuotation(id)
  if (doc.value?.status === 'Approved') {
    try {
      areaSummary.value = await api.getQuotationSalesOrderSummary(id)
    } catch (e) {
      console.warn('Failed to load area summary', e)
    }
  } else {
    areaSummary.value = null
  }
}

async function createOrderForArea(areaZone: string) {
  if (!doc.value?.name || convertingArea.value || busy.value) return
  convertingArea.value = areaZone
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const name = await api.createSalesOrder(doc.value.name, areaZone)
    createdOrder.value = name
    message.value = name ? `Transport Sales Order ${name} created for area "${areaZone}".` : `Transport Sales Order created for area "${areaZone}".`
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : `Unable to create Transport Sales Order for ${areaZone}.`
  } finally {
    convertingArea.value = null
    busy.value = false
  }
}

async function createOrder() {
  if (!doc.value?.name || busy.value) return
  const firstUnconverted = areaSummary.value?.areas.find((a) => !a.is_fully_converted)
  if (firstUnconverted) {
    await createOrderForArea(firstUnconverted.area_zone)
    return
  }
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const name = await api.createSalesOrder(doc.value.name)
    createdOrder.value = name
    message.value = name ? 'Transport Sales Order ' + name + ' created.' : 'Transport Sales Order created.'
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unable to create Transport Sales Order.'
  } finally {
    busy.value = false
  }
}

function formatDate(dateStr: string | undefined) {
  if (!dateStr) return '\u2014'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return dateStr
  }
}

function goToList() {
  router.push('/quotations')
}

function goToEdit() {
  if (doc.value?.name) {
    router.push('/quotations/' + encodeURIComponent(doc.value.name) + '/edit')
  }
}

onMounted(() => {
  void load().catch((e) => { error.value = e instanceof Error ? e.message : 'Unable to load quotation.' })
})
</script>

<template>
  <PageContainer>
    <PageHeader :title="pageTitle" :subtitle="subtitle">
      <template #actions>
        <Button variant="outline" @click="goToList">
          <ArrowLeft /> Quotations
        </Button>
        <Button v-if="showEditButton" variant="outline" @click="goToEdit">
          <Pencil /> Edit
        </Button>
        <Button v-if="showCreateOrderButton" :disabled="busy" @click="createOrder">
          <FilePlus2 /> Create sales order
        </Button>
        <Button variant="ghost" size="icon" aria-label="Refresh" @click="load">
          <RefreshCw />
        </Button>
      </template>
    </PageHeader>

    <div v-if="error" class="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{{ error }}</div>
    <div v-if="message" class="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{{ message }}</div>
    <LoadingState v-if="!doc && !error" />
    <div v-else-if="doc" class="space-y-5">
      <div class="grid gap-4 md:grid-cols-4">
        <div class="rounded-xl border bg-card p-4">
          <p class="label">Status</p>
          <Badge :variant="badge">{{ doc.status }}</Badge>
        </div>
        <div class="rounded-xl border bg-card p-4">
          <p class="label">Quotation date</p>
          <p>{{ formatDate(doc.quotation_date) }}</p>
        </div>
        <div class="rounded-xl border bg-card p-4">
          <p class="label">Valid until</p>
          <p>{{ formatDate(doc.valid_until) }}</p>
        </div>
        <div class="rounded-xl border bg-card p-4">
          <p class="label">Service period</p>
          <p>{{ formatDate(doc.service_period_from) }} \u2192 {{ formatDate(doc.service_period_to) }}</p>
        </div>
      </div>

      <section class="rounded-xl border bg-card p-5">
        <h2 class="section-title">
          <span class="inline-flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 text-primary"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> Overview</span>
        </h2>
        <div class="grid gap-4 sm:grid-cols-3">
          <div><p class="label">Customer</p><p>{{ doc.customer }}</p></div>
          <div><p class="label">Customer reference</p><p>{{ doc.customer_reference || '\u2014' }}</p></div>
          <div><p class="label">Currency</p><p>{{ doc.currency }}</p></div>
          <div><p class="label">Estimated quantity</p><p>{{ doc.estimated_quantity || '\u2014' }}</p></div>
          <div><p class="label">Estimated trips</p><p>{{ doc.estimated_trips || '\u2014' }}</p></div>
          <div><p class="label">Remarks</p><p>{{ doc.remarks || '\u2014' }}</p></div>
        </div>
      </section>

      <section class="rounded-xl border bg-card p-5">
        <h2 class="section-title">
          <span class="inline-flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 text-primary"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg> Materials & Route Coverage</span>
        </h2>
        <div v-if="doc.materials?.length" class="space-y-4">
          <div v-for="material in doc.materials" :key="material.material" class="rounded-lg border p-4 bg-muted/30">
            <p class="font-semibold text-foreground">{{ material.material }}</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2 text-sm">
              <div><span class="text-muted-foreground">Loading Points:</span><span class="ml-2 font-medium">{{ doc.locations?.filter(l => l.material === material.material && l.location_role === 'Loading').map(l => l.location).join(', ') || '\u2014' }}</span></div>
              <div><span class="text-muted-foreground">Destinations:</span><span class="ml-2 font-medium">{{ doc.locations?.filter(l => l.material === material.material && l.location_role === 'Destination').map(l => l.location).join(', ') || '\u2014' }}</span></div>
            </div>
          </div>
        </div>
        <p v-else class="text-sm text-muted-foreground">No materials found.</p>
      </section>

      <section v-if="doc.status === 'Approved' && areaSummary" class="rounded-xl border bg-card p-5">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <h2 class="section-title mb-0">
            <span class="inline-flex items-center gap-2">
              <MapPin class="w-5 h-5 text-primary" /> Area-wise Sales Orders
            </span>
          </h2>
          <div class="flex items-center gap-2 text-xs font-medium">
            <span class="text-muted-foreground">Areas converted:</span>
            <Badge :variant="areaSummary.has_unconverted_areas ? 'amber' : 'green'">
              {{ areaSummary.converted_areas }} of {{ areaSummary.total_areas }} converted
            </Badge>
          </div>
        </div>

        <p class="text-xs text-muted-foreground mb-4">
          Each Transport Sales Order covers exactly ONE geographical area. Generate separate Sales Orders for each area below.
        </p>

        <div v-if="areaSummary.areas?.length" class="space-y-4">
          <div
            v-for="area in areaSummary.areas"
            :key="area.area_zone"
            class="rounded-lg border p-4 transition-all"
            :class="area.is_fully_converted ? 'bg-muted/10 border-emerald-200' : 'bg-muted/30 border-border'"
          >
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-bold text-base text-foreground">{{ area.area_zone }}</span>
                  <Badge v-if="area.is_fully_converted" variant="green">Converted</Badge>
                  <Badge v-else-if="area.is_partially_converted" variant="amber">Partially Converted</Badge>
                  <Badge v-else variant="outline">Unconverted</Badge>
                  <span v-if="!area.has_valid_area" class="text-xs text-destructive font-medium">(Missing area config)</span>
                </div>
                <div class="mt-2 text-xs text-muted-foreground space-y-1">
                  <div>
                    <span class="font-semibold text-foreground/80">Materials:</span>
                    <span class="ml-1">{{ area.materials.join(', ') || '—' }}</span>
                  </div>
                  <div>
                    <span class="font-semibold text-foreground/80">Loading Points:</span>
                    <span class="ml-1">{{ area.loading_locations.join(', ') || '—' }}</span>
                  </div>
                  <div>
                    <span class="font-semibold text-foreground/80">Destinations:</span>
                    <span class="ml-1">{{ area.unloading_locations.join(', ') || '—' }}</span>
                  </div>
                  <div>
                    <span class="font-semibold text-foreground/80">Rate Coverage:</span>
                    <span class="ml-1">{{ area.converted_rates }} of {{ area.total_rates }} rates converted</span>
                  </div>
                </div>
              </div>

              <div class="flex flex-col sm:items-end gap-2 shrink-0">
                <div v-if="area.sales_orders?.length" class="flex flex-wrap gap-1 items-center">
                  <span class="text-xs text-muted-foreground mr-1">Orders:</span>
                  <span
                    v-for="so in area.sales_orders"
                    :key="so.sales_order"
                    class="inline-flex items-center gap-1 rounded bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800"
                  >
                    {{ so.sales_order }} ({{ so.status }})
                  </span>
                </div>

                <Button
                  v-if="!area.is_fully_converted"
                  size="sm"
                  :disabled="convertingArea === area.area_zone || busy"
                  @click="createOrderForArea(area.area_zone)"
                >
                  <FilePlus2 class="w-4 h-4 mr-1" />
                  <span v-if="convertingArea === area.area_zone">Creating...</span>
                  <span v-else>Create Sales Order for {{ area.area_zone }}</span>
                </Button>
                <div v-else class="text-xs text-emerald-600 font-medium flex items-center gap-1">
                  <CheckCircle2 class="w-4 h-4" /> Fully Converted
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="!areaSummary.has_unconverted_areas" class="mt-4 rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 class="w-4 h-4 text-emerald-600" />
          All geographical areas in this quotation have been converted to active Transport Sales Orders.
        </div>
      </section>

      <section class="rounded-xl border bg-card p-5">
        <h2 class="section-title">
          <span class="inline-flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 text-primary"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="6" x2="12" y2="18"></line><line x1="6" y1="12" x2="18" y2="12"></line></svg> Commercial Rate Schedule</span>
        </h2>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[850px] text-sm">
            <thead><tr class="border-b text-left text-xs uppercase text-muted-foreground"><th class="p-2">Material</th><th class="p-2">Loading</th><th class="p-2">Destination</th><th class="p-2">Rate / TON</th><th class="p-2">Effective period</th></tr></thead>
            <tbody><tr v-for="row in doc.rates" :key="row.name ?? row.material + '-' + row.effective_from" class="border-b"><td class="p-2 font-semibold">{{ row.material }}</td><td class="p-2">{{ row.loading_location }}</td><td class="p-2">{{ row.unloading_location }}</td><td class="p-2">{{ doc.currency }} {{ row.rate }}</td><td class="p-2">{{ formatDate(row.effective_from) }} \u2192 {{ formatDate(row.effective_to) }}</td></tr></tbody>
          </table>
          <p v-if="!doc.rates?.length" class="py-6 text-center text-sm text-muted-foreground">No rate rows.</p>
        </div>
      </section>

      <section v-if="doc.estimated_quantity || doc.estimated_trips" class="rounded-xl border bg-card p-5">
        <h2 class="section-title">
          <span class="inline-flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 text-primary"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg> Estimated Transportation Requirement</span>
        </h2>
        <div class="grid gap-4 sm:grid-cols-4 text-sm">
          <div class="bg-muted/30 p-3 rounded-lg"><p class="label">Estimated Volume</p><p>{{ doc.estimated_quantity }} TON/month</p></div>
          <div class="bg-muted/30 p-3 rounded-lg"><p class="label">Truck Type</p><p>{{ doc.customer_approval_notes || '\u2014' }}</p></div>
          <div class="bg-muted/30 p-3 rounded-lg"><p class="label">Frequency</p><p>\u2014</p></div>
          <div class="bg-muted/30 p-3 rounded-lg"><p class="label">Est. Trips/Day</p><p>{{ doc.estimated_trips }}</p></div>
        </div>
      </section>

      <section class="rounded-xl border bg-card p-5">
        <h2 class="section-title">
          <span class="inline-flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 text-primary"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg> Approval Record</span>
        </h2>
        <div class="grid gap-4 sm:grid-cols-3">
          <div><p class="label">Approval date</p><p>{{ formatDate(doc.customer_approval_date) || 'Not recorded' }}</p></div>
          <div><p class="label">Approval reference</p><p>{{ doc.customer_approval_reference || '\u2014' }}</p></div>
          <div><p class="label">Approval notes</p><p>{{ doc.customer_approval_notes || '\u2014' }}</p></div>
        </div>
      </section>

      <section v-if="createdOrder" class="rounded-xl border bg-emerald-50 border-emerald-200 p-5">
        <h2 class="section-title">
          <span class="inline-flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 text-green-600"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> Linked Sales Order</span>
        </h2>
        <p class="font-semibold text-green-800">{{ createdOrder }}</p>
        <p class="text-sm text-green-700 mt-1">This quotation has been converted to a Transport Sales Order.</p>
      </section>
    </div>
  </PageContainer>
</template>

<style scoped>
.label { @apply mb-1 text-xs font-bold uppercase tracking-wide text-muted-foreground; }
.section-title { @apply mb-4 text-lg font-bold; }
</style>