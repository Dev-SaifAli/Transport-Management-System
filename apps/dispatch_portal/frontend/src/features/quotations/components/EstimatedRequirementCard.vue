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
  <div class="bg-card rounded-xl border border-border/90 shadow-sm transition-all duration-200 overflow-hidden">
    <!-- Header -->
    <div
      class="p-4 sm:p-5 flex items-center justify-between cursor-pointer select-none bg-card hover:bg-accent/50 transition"
      @click="isExpanded = !isExpanded"
    >
      <div class="flex items-center gap-3.5">
        <div class="w-10 h-10 rounded-lg bg-muted text-muted-foreground flex items-center justify-center shrink-0 border border-border shadow-2xs">
          <BarChart3 class="w-5 h-5" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-bold text-foreground text-base">
              Estimated Transportation Requirement
            </h3>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-muted text-muted-foreground uppercase tracking-wider">
              OPTIONAL
            </span>
          </div>
          <p class="text-xs text-muted-foreground mt-0.5">
            Planning only — estimates never limit operational trips
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button class="p-1.5 text-muted-foreground hover:text-foreground rounded-lg transition">
          <ChevronUp v-if="isExpanded" class="w-5 h-5" />
          <ChevronDown v-else class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- Expanded Body -->
    <div v-show="isExpanded" class="border-t border-border p-5 sm:p-6 space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Estimated Volume (Monthly)
          </label>
          <div class="relative">
            <input
              type="number"
              v-model.number="quotationStore.quotation.estimatedRequirement.estimatedVolume"
              class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 pr-14 outline-none focus:border-ring"
            />
            <span class="absolute right-3 top-2.5 text-xs text-muted-foreground font-mono">
              {{ quotationStore.quotation.estimatedRequirement.volumeUom }}
            </span>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Fleet / Truck Specification
          </label>
          <select
            v-model="quotationStore.quotation.estimatedRequirement.truckType"
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 outline-none focus:border-ring"
          >
            <option v-for="t in truckTypes" :key="t" :value="t">
              {{ t }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Delivery Frequency
          </label>
          <select
            v-model="quotationStore.quotation.estimatedRequirement.frequency"
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 outline-none focus:border-ring"
          >
            <option v-for="f in frequencies" :key="f" :value="f">
              {{ f }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Estimated Trips / Day
          </label>
          <input
            type="number"
            v-model.number="quotationStore.quotation.estimatedRequirement.estimatedTripsPerDay"
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 outline-none focus:border-ring"
          />
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-foreground mb-1.5">
          Operational Logistics Notes
        </label>
        <textarea
          rows="2"
          v-model="quotationStore.quotation.estimatedRequirement.notes"
          placeholder="Special site gate passes, safety inductions, weighbridge requirements..."
          class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 placeholder:text-muted-foreground outline-none focus:border-ring"
        ></textarea>
      </div>
    </div>
  </div>
</template>