<script setup lang="ts">
import { FileText, Plus, RefreshCw, Search } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import EmptyState from '@/components/shared/EmptyState.vue'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useQuotationsStore } from '@/stores/quotations'
import type { QuotationStatus } from '@/types/quotations'

const quotations = useQuotationsStore()
const router = useRouter()
const statusLabels: Record<QuotationStatus, string> = {
  draft: 'Draft',
  approved: 'Approved',
  cancelled: 'Cancelled',
}

const hasFilters = computed(() => quotations.activePills.length > 0 || quotations.search.length > 0)

function statusVariant(status: QuotationStatus): 'blue' | 'amber' | 'green' | 'red' {
  if (status === 'approved') return 'green'
  if (status === 'draft') return 'blue'
  if (status === 'cancelled') return 'red'
  return 'red'
}

function refresh(): void {
  void quotations.fetchQuotations()
}

onMounted(refresh)
</script>

<template>
  <PageContainer>
    <PageHeader title="Transport Quotations" subtitle="Review customer rates and approval status.">
      <template #actions>
        <Button variant="outline" :disabled="quotations.status === 'loading'" @click="refresh">
          <RefreshCw aria-hidden="true" />
          Refresh
        </Button>
        <Button @click="router.push('/quotations/new')">
          <Plus aria-hidden="true" />
          New quotation
        </Button>
      </template>
    </PageHeader>

    <div class="space-y-4">
      <div class="flex flex-col gap-3 rounded-xl border bg-card p-4 shadow-sm lg:flex-row lg:items-center">
        <div class="relative min-w-0 flex-1 lg:max-w-md">
          <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input v-model="quotations.search" class="pl-9" placeholder="Search quotations, customers, materials…" aria-label="Search quotations" />
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="tab in quotations.tabs"
            :key="tab.key"
            type="button"
            class="rounded-lg border px-3 py-2 text-sm font-semibold transition-colors hover:bg-accent"
            :class="quotations.activeTab === tab.key ? 'border-primary bg-accent text-accent-foreground' : 'bg-card text-muted-foreground'"
            @click="quotations.activeTab = tab.key"
          >
            {{ tab.label }}
            <Badge variant="muted" class="ml-1">{{ tab.count }}</Badge>
          </button>
        </div>
      </div>

      <div v-if="hasFilters" class="flex items-center justify-between gap-3 text-sm text-muted-foreground">
        <span>{{ quotations.showingLabel }}</span>
        <Button variant="link" size="sm" @click="quotations.clearAllFilters">Clear filters</Button>
      </div>

      <div v-if="quotations.status === 'loading'" class="rounded-xl border bg-card p-10 text-center text-muted-foreground">
        Loading quotations…
      </div>
      <div v-else-if="quotations.status === 'error'" class="rounded-xl border border-destructive/30 bg-card p-10 text-center text-destructive">
        {{ quotations.error }}
        <div class="mt-4"><Button variant="outline" @click="refresh">Try again</Button></div>
      </div>
      <div v-else-if="quotations.pageRows.length === 0" class="rounded-xl border bg-card">
        <EmptyState title="No quotations found" description="Try changing the search or status filter." />
      </div>
      <div v-else class="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full min-w-[900px] text-left text-sm">
            <thead class="border-b bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th class="px-5 py-3">Quotation</th>
                <th class="px-5 py-3">Customer</th>
                <th class="px-5 py-3">Date</th>
                <th class="px-5 py-3">Valid until</th>
                <th class="px-5 py-3">Materials</th>
                <th class="px-5 py-3">Routes</th>
                <th class="px-5 py-3">Rate lines</th>
                <th class="px-5 py-3">Status</th>
                <th class="px-5 py-3">Created by</th>
              </tr>
            </thead>
            <tbody class="divide-y">
              <tr v-for="row in quotations.pageRows" :key="row.id" class="cursor-pointer transition-colors hover:bg-muted/30" @click="router.push(`/quotations/${encodeURIComponent(row.id)}`)">
                <td class="px-5 py-4 font-semibold text-foreground"><FileText class="mr-2 inline size-4 text-muted-foreground" />{{ row.id }}</td>
                <td class="px-5 py-4">{{ row.customer }}</td>
                <td class="px-5 py-4 text-muted-foreground">{{ row.quotationDate }}</td>
                <td class="px-5 py-4 text-muted-foreground">{{ row.validUntil }}</td>
                <td class="max-w-[220px] truncate px-5 py-4">{{ row.materials }}</td>
                <td class="px-5 py-4 text-muted-foreground">{{ row.locationCount ?? '—' }}</td>
                <td class="px-5 py-4 tabular-nums">{{ row.rateLines }}</td>
                <td class="px-5 py-4"><Badge :variant="statusVariant(row.status)">{{ statusLabels[row.status] }}</Badge></td>
                <td class="px-5 py-4 text-muted-foreground">{{ row.createdBy }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="flex items-center justify-between border-t px-5 py-3 text-sm text-muted-foreground">
          <span>{{ quotations.showingLabel }}</span>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" :disabled="quotations.pageIndex === 0" @click="quotations.setPage(quotations.pageIndex - 1)">Previous</Button>
            <Button variant="outline" size="sm" :disabled="quotations.pageIndex >= quotations.pageCount - 1" @click="quotations.setPage(quotations.pageIndex + 1)">Next</Button>
          </div>
        </div>
      </div>
    </div>
  </PageContainer>
</template>
