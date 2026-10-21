<script setup lang="ts">
import { ref } from 'vue'
import { useQuotationFormStore } from '../stores/quotationForm'
import { BarChart3, ChevronDown, ChevronUp } from 'lucide-vue-next'

const quotationStore = useQuotationFormStore()
const isExpanded = ref(false)

const truckTypes = [
  'Tipper 45m3 (Bulk Aggregates & Stone)',
  'Heavy Flatbed 40ft (General Cargo & Steel)',
  'Bulk Cement Silo Tanker 38m3',
  'Lowbed Heavy Hauler (Machinery)',
  'Curtainsider 13.6m',
]

const frequencies = [
  'Daily continuous (2-3 shifts/day)',
  'Daily standard day shift',
  'Weekly scheduled batches',
  'On-demand call-off basis',
]
</script>

<template>
  <div class="bg-white rounded-xl border border-slate-200/90 shadow-xs transition-all duration-200 overflow-hidden">
    <!-- Header -->
    <div
      class="p-4 sm:p-5 flex items-center justify-between cursor-pointer select-none bg-slate-50/50 hover:bg-slate-100/60 transition border-b border-slate-100"
      @click="isExpanded = !isExpanded"
    >
      <div class="flex items-center gap-3.5">
        <div class="w-10 h-10 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0 border border-slate-200 shadow-2xs">
          <BarChart3 class="w-5 h-5" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-bold text-slate-900 text-base">
              Estimated Transportation Requirement
            </h3>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 uppercase tracking-wider border border-slate-200/70">
              OPTIONAL
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-0.5">
            Planning only — estimates never limit operational trips
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button class="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg transition">
          <ChevronUp v-if="isExpanded" class="w-5 h-5" />
          <ChevronDown v-else class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- Expanded Body -->
    <div v-show="isExpanded" class="p-5 sm:p-6 space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1.5">
            Estimated Volume (Monthly)
          </label>
          <div class="relative">
            <input
              type="number"
              v-model.number="quotationStore.quotation.estimatedRequirement.estimatedVolume"
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 pr-14 text-sm text-slate-900 shadow-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            />
            <span class="absolute right-3 top-2.5 text-xs text-slate-400 font-mono">
              {{ quotationStore.quotation.estimatedRequirement.volumeUom }}
            </span>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1.5">
            Fleet / Truck Specification
          </label>
          <select
            v-model="quotationStore.quotation.estimatedRequirement.truckType"
            class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
          >
            <option v-for="t in truckTypes" :key="t" :value="t">
              {{ t }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1.5">
            Delivery Frequency
          </label>
          <select
            v-model="quotationStore.quotation.estimatedRequirement.frequency"
            class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
          >
            <option v-for="f in frequencies" :key="f" :value="f">
              {{ f }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1.5">
            Estimated Trips / Day
          </label>
          <input
            type="number"
            v-model.number="quotationStore.quotation.estimatedRequirement.estimatedTripsPerDay"
            class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
          />
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-700 mb-1.5">
          Operational Logistics Notes
        </label>
        <textarea
          rows="2"
          v-model="quotationStore.quotation.estimatedRequirement.notes"
          placeholder="Special site gate passes, safety inductions, weighbridge requirements..."
          class="w-full rounded-lg border border-slate-300 bg-white p-3 text-sm text-slate-900 placeholder:text-slate-400 shadow-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
        ></textarea>
      </div>
    </div>
  </div>
</template>