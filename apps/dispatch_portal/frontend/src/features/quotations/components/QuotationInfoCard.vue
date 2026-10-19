<script setup lang="ts">
import { computed } from 'vue'
import { useQuotationFormStore } from '../stores/quotationForm'
import TomSelect from './TomSelect.vue'
import { FileText, Lock, ChevronUp, Check } from 'lucide-vue-next'

const quotationStore = useQuotationFormStore()

const customerOptions = computed(() => {
  return quotationStore.customerOptions.map((c: { value: string; text: string; subtext?: string }) => ({
    value: c.value,
    text: c.text,
    subtext: c.subtext,
  }))
})

const currencyOptions = [
  { value: 'AED', text: 'AED — UAE Dirham' },
  { value: 'SAR', text: 'SAR — Saudi Riyal' },
  { value: 'USD', text: 'USD — US Dollar' },
  { value: 'EUR', text: 'EUR — Euro' },
]

function onCustomerChange(val: string | string[]) {
  const value = Array.isArray(val) ? (val[0] ?? '') : val
  quotationStore.quotation.customerId = value
  const found = quotationStore.masters.customers.find((c: { value: string; text: string }) => c.value === value)
  quotationStore.quotation.customerName = found ? found.text : value
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const day = String(d.getDate()).padStart(2, '0')
    const month = d.toLocaleString('en-US', { month: 'short' })
    const year = d.getFullYear()
    return `${day} ${month} ${year}`
  } catch {
    return dateStr
  }
}
</script>

<template>
  <div class="bg-card rounded-xl border border-border/90 shadow-sm transition-all duration-200 overflow-hidden">
    <!-- Collapsed View (Summary Card) -->
    <div
      v-if="!quotationStore.isEditingInfo && quotationStore.quotation.customerName"
      class="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4"
    >
      <div class="flex items-start sm:items-center gap-3.5">
        <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20">
          <FileText class="w-5 h-5" />
        </div>
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-semibold text-foreground text-sm sm:text-base font-mono">
              {{ quotationStore.quotation.quotationNumber }}
            </span>
            <span class="text-muted-foreground">·</span>
            <span class="font-semibold text-foreground text-sm sm:text-base">
              {{ quotationStore.quotation.customerName }}
            </span>
          </div>
          <div class="text-xs text-muted-foreground mt-0.5 flex flex-wrap items-center gap-2">
            <span>Quotation date {{ formatDate(quotationStore.quotation.quotationDate) }}</span>
            <span class="text-muted-foreground">·</span>
            <span>Valid until {{ formatDate(quotationStore.quotation.validUntil) }}</span>
            <span class="text-muted-foreground">·</span>
            <span>Currency {{ quotationStore.quotation.currency }}</span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-3 self-end md:self-auto">
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground border border-border">
          <span class="w-1.5 h-1.5 rounded-full bg-muted-foreground"></span>
          {{ quotationStore.quotation.status.toUpperCase() }}
        </span>
        <button
          @click="quotationStore.isEditingInfo = true"
          class="text-xs font-semibold text-primary hover:text-primary/80 px-2.5 py-1 rounded hover:bg-accent transition cursor-pointer"
        >
          Edit
        </button>
      </div>
    </div>

    <!-- Expanded View (Full Editable Form) -->
    <div v-else class="p-5 sm:p-6">
      <div class="flex items-center justify-between border-b border-border pb-4 mb-5">
        <div>
          <h2 class="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
            Quotation Information
          </h2>
          <p class="text-xs text-muted-foreground mt-0.5">
            Number is auto-generated · Customer is linked to the ERPNext Customer master
          </p>
        </div>
        <button
          v-if="quotationStore.quotation.customerName"
          @click="quotationStore.isEditingInfo = false"
          class="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 px-2 py-1 rounded hover:bg-accent transition cursor-pointer"
        >
          <span>Collapse</span>
          <ChevronUp class="w-4 h-4" />
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <!-- Quotation Number -->
        <div>
          <label class="block text-xs font-semibold text-muted-foreground mb-1.5">
            Quotation Number
          </label>
          <div class="relative flex items-center">
            <input
              type="text"
              readonly
              :value="quotationStore.quotation.quotationNumber"
              class="w-full bg-muted/40 border border-border text-foreground text-sm rounded-lg px-3.5 py-2.5 font-mono cursor-not-allowed focus:outline-none"
            />
            <div class="absolute right-2.5 flex items-center gap-1.5">
              <span class="bg-primary/10 text-primary text-[10px] font-bold px-1.5 py-0.5 rounded tracking-wide">
                AUTO
              </span>
              <Lock class="w-3.5 h-3.5 text-muted-foreground" />
            </div>
          </div>
        </div>

        <!-- Customer with TomSelect Search -->
        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Customer <span class="text-destructive ml-1">*</span>
          </label>
          <TomSelect
            :model-value="quotationStore.quotation.customerId || quotationStore.quotation.customerName"
            :options="customerOptions"
            placeholder="Search customers..."
            @update:model-value="onCustomerChange"
          />
        </div>

        <!-- Quotation Date -->
        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Quotation Date
          </label>
          <input
            type="date"
            v-model="quotationStore.quotation.quotationDate"
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
          />
        </div>

        <!-- Valid Until -->
        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Valid Until <span class="text-destructive ml-1">*</span>
          </label>
          <input
            type="date"
            v-model="quotationStore.quotation.validUntil"
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
          />
        </div>

        <!-- Company -->
        <div>
          <label class="block text-xs font-semibold text-muted-foreground mb-1.5">
            Company
          </label>
          <div class="relative">
            <input
              type="text"
              readonly
              :value="quotationStore.quotation.company"
              class="w-full bg-muted/40 border border-border text-muted-foreground text-sm rounded-lg px-3 py-2 cursor-not-allowed focus:outline-none"
            />
          </div>
        </div>

        <!-- Currency -->
        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Currency
          </label>
          <select
            v-model="quotationStore.quotation.currency"
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
          >
            <option v-for="c in currencyOptions" :key="c.value" :value="c.value">
              {{ c.text }}
            </option>
          </select>
        </div>

        <!-- Customer Reference -->
        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Customer Reference
          </label>
          <input
            type="text"
            v-model="quotationStore.quotation.customerReference"
            placeholder="PO / email reference — optional"
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
          />
        </div>

        <!-- Remarks -->
        <div class="md:col-span-2">
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Remarks
          </label>
          <input
            type="text"
            v-model="quotationStore.quotation.remarks"
            placeholder="Optional notes for the customer..."
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
          />
        </div>
      </div>

      <div v-if="quotationStore.quotation.customerName" class="mt-4 pt-3 flex justify-end">
        <button
          @click="quotationStore.isEditingInfo = false"
          class="inline-flex items-center gap-1.5 text-xs font-semibold text-foreground bg-muted hover:bg-muted/80 px-3.5 py-1.5 rounded-lg transition cursor-pointer"
        >
          <Check class="w-3.5 h-3.5 text-green-600" />
          <span>Save Information & Continue</span>
        </button>
      </div>
    </div>
  </div>
</template>