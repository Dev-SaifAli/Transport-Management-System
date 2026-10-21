<script setup lang="ts">
import { computed } from 'vue'
import { useQuotationFormStore } from '../stores/quotationForm'
import MasterSelect from '@/components/shared/MasterSelect.vue'
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
  <div class="bg-white rounded-xl border border-slate-200/90 shadow-xs transition-all duration-200 overflow-hidden">
    <!-- Collapsed View (Summary Card) -->
    <div
      v-if="!quotationStore.isEditingInfo && quotationStore.quotation.customerName"
      class="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4"
    >
      <div class="flex items-start sm:items-center gap-3.5">
        <div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-200/60 shadow-2xs">
          <FileText class="w-5 h-5" />
        </div>
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-semibold text-slate-900 text-sm sm:text-base font-mono">
              {{ quotationStore.quotation.quotationNumber }}
            </span>
            <span class="text-slate-400">·</span>
            <span class="font-semibold text-slate-900 text-sm sm:text-base">
              {{ quotationStore.quotation.customerName }}
            </span>
          </div>
          <div class="text-xs text-slate-500 mt-0.5 flex flex-wrap items-center gap-2">
            <span>Quotation date {{ formatDate(quotationStore.quotation.quotationDate) }}</span>
            <span class="text-slate-400">·</span>
            <span>Valid until {{ formatDate(quotationStore.quotation.validUntil) }}</span>
            <span class="text-slate-400">·</span>
            <span>Currency {{ quotationStore.quotation.currency }}</span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-3 self-end md:self-auto">
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
          <span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
          {{ quotationStore.quotation.status.toUpperCase() }}
        </span>
        <button
          @click="quotationStore.isEditingInfo = true"
          class="text-xs font-semibold text-blue-600 hover:text-blue-700 px-2.5 py-1 rounded-lg hover:bg-blue-50 transition cursor-pointer"
        >
          Edit
        </button>
      </div>
    </div>

    <!-- Expanded View (Full Editable Form) -->
    <div v-else>
      <div class="bg-slate-50/50 border-b border-slate-100 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 class="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
            Quotation Information
          </h2>
          <p class="text-xs text-slate-500 mt-0.5">
            Number is auto-generated · Customer is linked to the ERPNext Customer master
          </p>
        </div>
        <button
          v-if="quotationStore.quotation.customerName"
          @click="quotationStore.isEditingInfo = false"
          class="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 px-2.5 py-1.5 rounded-lg hover:bg-slate-100 transition cursor-pointer"
        >
          <span>Collapse</span>
          <ChevronUp class="w-4 h-4" />
        </button>
      </div>

      <div class="p-6">
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
          <!-- Row 1: Quotation Number (2 cols) -->
          <div class="col-span-1 md:col-span-2">
            <label class="block text-xs font-semibold text-slate-500 mb-1.5">
              Quotation Number
            </label>
            <div class="relative flex items-center">
              <input
                type="text"
                readonly
                :value="quotationStore.quotation.quotationNumber"
                class="h-10 w-full rounded-lg border border-slate-200 bg-slate-100/80 px-3 pr-14 text-sm font-mono text-slate-500 cursor-not-allowed select-none focus:outline-none"
              />
              <div class="pointer-events-none absolute right-2.5 flex items-center gap-1.5">
                <span class="rounded border border-blue-200/80 bg-blue-50 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-blue-700">
                  AUTO
                </span>
                <Lock class="size-3.5 text-slate-400" />
              </div>
            </div>
          </div>

          <!-- Row 1: Customer (6 cols) -->
          <div class="col-span-1 md:col-span-6">
            <MasterSelect
              label="Customer"
              :required="true"
              doctype="Customer"
              create-url="/app/customer/new"
              :model-value="quotationStore.quotation.customerId || quotationStore.quotation.customerName"
              :options="customerOptions"
              :max-options="7"
              :loading="quotationStore.masterLoading.customers"
              placeholder="Search customers..."
              @update:model-value="onCustomerChange"
              @refresh="quotationStore.loadMasters()"
              @search="quotationStore.searchCustomers($event)"
            />
          </div>

          <!-- Row 1: Quotation Date (2 cols) -->
          <div class="col-span-1 md:col-span-2">
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">
              Quotation Date
            </label>
            <input
              type="date"
              v-model="quotationStore.quotation.quotationDate"
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs transition hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            />
          </div>

          <!-- Row 1: Valid Until (2 cols) -->
          <div class="col-span-1 md:col-span-2">
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">
              Valid Until <span class="text-rose-500 ml-0.5">*</span>
            </label>
            <input
              type="date"
              v-model="quotationStore.quotation.validUntil"
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs transition hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            />
          </div>

          <!-- Row 2: Company (4 cols) -->
          <div class="col-span-1 md:col-span-4">
            <label class="block text-xs font-semibold text-slate-500 mb-1.5">
              Company
            </label>
            <input
              type="text"
              readonly
              :value="quotationStore.quotation.company"
              class="h-10 w-full rounded-lg border border-slate-200 bg-slate-100/80 px-3 py-2 text-sm text-slate-500 cursor-not-allowed select-none focus:outline-none"
            />
          </div>

          <!-- Row 2: Currency (2 cols) -->
          <div class="col-span-1 md:col-span-2">
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">
              Currency
            </label>
            <select
              v-model="quotationStore.quotation.currency"
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs transition hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            >
              <option v-for="c in currencyOptions" :key="c.value" :value="c.value">
                {{ c.text }}
              </option>
            </select>
          </div>

          <!-- Row 2: Customer Reference (3 cols) -->
          <div class="col-span-1 md:col-span-3">
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">
              Customer Reference
            </label>
            <input
              type="text"
              v-model="quotationStore.quotation.customerReference"
              placeholder="PO / email reference — optional"
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 shadow-xs transition hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            />
          </div>

          <!-- Row 2: Remarks (3 cols) -->
          <div class="col-span-1 md:col-span-3">
            <label class="block text-xs font-semibold text-slate-700 mb-1.5">
              Remarks
            </label>
            <input
              type="text"
              v-model="quotationStore.quotation.remarks"
              placeholder="Optional notes for the customer..."
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 shadow-xs transition hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            />
          </div>
        </div>

        <div v-if="quotationStore.quotation.customerName" class="mt-5 pt-3 flex justify-end border-t border-slate-100">
          <button
            @click="quotationStore.isEditingInfo = false"
            class="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 px-3.5 py-2 rounded-lg transition cursor-pointer"
          >
            <Check class="w-3.5 h-3.5 text-emerald-600" />
            <span>Save Information & Continue</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>