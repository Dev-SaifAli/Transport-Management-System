<script setup lang="ts">
import { ArrowLeft, FilePlus2, Pencil, RefreshCw } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import LoadingState from '@/components/shared/LoadingState.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { createQuotationsService } from '@/services/api/quotations'
import type { TransportQuotationDoc } from '@/types/quotations'

const route = useRoute(); const router = useRouter(); const api = createQuotationsService(); const doc = ref<TransportQuotationDoc | null>(null); const error = ref(''); const busy = ref(false); const message = ref(''); const createdOrder = ref('')
const badge = computed(() => doc.value?.status === 'Approved' ? 'green' : doc.value?.status === 'Cancelled' ? 'red' : 'blue')
async function load() { error.value = ''; doc.value = await api.getQuotation(route.params.id as string) }
async function createOrder() { if (!doc.value?.name || createdOrder.value) return; busy.value = true; try { const name = await api.createSalesOrder(doc.value.name); createdOrder.value = name; message.value = name ? `Transport Sales Order ${name} created.` : 'Transport Sales Order created.' } catch (e) { error.value = e instanceof Error ? e.message : 'Unable to create Transport Sales Order.' } finally { busy.value = false } }
onMounted(() => { void load().catch((e) => { error.value = e instanceof Error ? e.message : 'Unable to load quotation.' }) })
</script>
<template>
  <PageContainer><PageHeader :title="doc?.name ?? 'Quotation'" :subtitle="doc?.customer ? `${doc.customer} · AED` : 'Quotation details'">
    <template #actions><Button variant="outline" @click="router.push('/quotations')"><ArrowLeft /> Quotations</Button><Button v-if="doc?.status === 'Draft'" variant="outline" @click="router.push(`/quotations/${encodeURIComponent(doc.name ?? '')}/edit`)"><Pencil /> Edit</Button><Button v-if="doc?.status === 'Approved' && !createdOrder" :disabled="busy" @click="createOrder"><FilePlus2 /> Create sales order</Button><Button variant="ghost" size="icon" aria-label="Refresh" @click="load"><RefreshCw /></Button></template>
  </PageHeader>
  <div v-if="error" class="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{{ error }}</div><div v-if="message" class="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{{ message }}</div>
  <LoadingState v-if="!doc && !error" />
  <div v-else-if="doc" class="space-y-5"><div class="grid gap-4 md:grid-cols-4"><div class="rounded-xl border bg-card p-4"><p class="label">Status</p><Badge :variant="badge">{{ doc.status }}</Badge></div><div class="rounded-xl border bg-card p-4"><p class="label">Quotation date</p><p>{{ doc.quotation_date || '—' }}</p></div><div class="rounded-xl border bg-card p-4"><p class="label">Valid until</p><p>{{ doc.valid_until || '—' }}</p></div><div class="rounded-xl border bg-card p-4"><p class="label">Service period</p><p>{{ doc.service_period_from || '—' }} → {{ doc.service_period_to || '—' }}</p></div></div>
    <section class="rounded-xl border bg-card p-5"><h2 class="section-title">Overview</h2><div class="grid gap-4 sm:grid-cols-3"><div><p class="label">Customer</p><p>{{ doc.customer }}</p></div><div><p class="label">Customer reference</p><p>{{ doc.customer_reference || '—' }}</p></div><div><p class="label">Currency</p><p>{{ doc.currency }}</p></div><div><p class="label">Estimated quantity</p><p>{{ doc.estimated_quantity || '—' }}</p></div><div><p class="label">Estimated trips</p><p>{{ doc.estimated_trips || '—' }}</p></div><div><p class="label">Remarks</p><p>{{ doc.remarks || '—' }}</p></div></div></section>
    <section class="rounded-xl border bg-card p-5"><h2 class="section-title">Rate schedule</h2><div class="overflow-x-auto"><table class="w-full min-w-[850px] text-sm"><thead><tr class="border-b text-left text-xs uppercase text-muted-foreground"><th class="p-2">Material</th><th class="p-2">Loading</th><th class="p-2">Destination</th><th class="p-2">Rate / TON</th><th class="p-2">Effective period</th></tr></thead><tbody><tr v-for="row in doc.rates" :key="row.name ?? `${row.material}-${row.effective_from}`" class="border-b"><td class="p-2 font-semibold">{{ row.material }}</td><td class="p-2">{{ row.loading_location }}</td><td class="p-2">{{ row.unloading_location }}</td><td class="p-2">AED {{ row.rate }}</td><td class="p-2">{{ row.effective_from }} → {{ row.effective_to }}</td></tr></tbody></table><p v-if="!doc.rates?.length" class="py-6 text-center text-sm text-muted-foreground">No rate rows.</p></div></section>
    <section class="rounded-xl border bg-card p-5"><h2 class="section-title">Approval record</h2><div class="grid gap-4 sm:grid-cols-3"><div><p class="label">Approval date</p><p>{{ doc.customer_approval_date || 'Not recorded' }}</p></div><div><p class="label">Approval reference</p><p>{{ doc.customer_approval_reference || '—' }}</p></div><div><p class="label">Approval notes</p><p>{{ doc.customer_approval_notes || '—' }}</p></div></div></section>
  </div></PageContainer>
</template>
<style scoped>.label { @apply mb-1 text-xs font-bold uppercase tracking-wide text-muted-foreground; }.section-title { @apply mb-4 text-lg font-bold; }</style>
