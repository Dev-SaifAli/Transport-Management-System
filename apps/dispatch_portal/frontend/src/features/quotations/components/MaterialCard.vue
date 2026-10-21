<script setup lang="ts">
import { computed, ref } from 'vue'
import type { QuotationMaterial } from '../types'
import { useQuotationFormStore } from '../stores/quotationForm'
import MasterSelect from '@/components/shared/MasterSelect.vue'
import { useDebounce } from '@/composables/useDebounce'
import {
  Box,
  Trash2,
  ChevronUp,
  ChevronDown,
  CheckCircle2,
  Info,
  Search,
  X,
  MapPin,
} from 'lucide-vue-next'

const props = defineProps<{
  material: QuotationMaterial
  index: number
}>()

const quotationStore = useQuotationFormStore()

const searchQuery = ref('')
const debouncedSearchQuery = useDebounce(searchQuery, 300)

// Unique geographical areas from loading points
const areaOptions = computed((): { value: string; text: string }[] => {
  return quotationStore.areaOptions
})

// Destination options for TomSelect
const destinationOptions = computed(() => {
  return quotationStore.masters.destinations.map((d: { id: string; name: string; emirate: string }) => ({
    value: d.id,
    text: d.name,
    subtext: d.emirate || undefined,
  }))
})

// Filtered loading points for the checkbox list (debounced)
const filteredLoadingPoints = computed(() => {
  const q = debouncedSearchQuery.value.trim().toLowerCase()
  return quotationStore.masters.locations.filter((point: { name: string; area: string; address?: string }) => {
    const matchesArea = !props.material.selectedLoadingAreaFilter || point.area === props.material.selectedLoadingAreaFilter
    const matchesSearch = !q || point.name.toLowerCase().includes(q) || point.area.toLowerCase().includes(q) || (point.address && point.address.toLowerCase().includes(q))
    return matchesArea && matchesSearch
  })
})

const allFilteredSelected = computed(() => {
  if (filteredLoadingPoints.value.length === 0) return false
  return filteredLoadingPoints.value.every((p) => props.material.selectedLoadingPointIds.includes(p.id))
})

function handleToggleSelectFiltered() {
  const current = new Set(props.material.selectedLoadingPointIds)
  if (allFilteredSelected.value) {
    filteredLoadingPoints.value.forEach((p) => current.delete(p.id))
  } else {
    filteredLoadingPoints.value.forEach((p) => current.add(p.id))
  }
  props.material.selectedLoadingPointIds = Array.from(current)
}

// Count of points in selected area
const pointsInSelectedAreaCount = computed(() => {
  if (!props.material.selectedLoadingAreaFilter) return quotationStore.masters.locations.length
  return quotationStore.masters.locations.filter((p: { area: string }) => p.area === props.material.selectedLoadingAreaFilter).length
})

const selectedInAreaCount = computed(() => {
  if (!props.material.selectedLoadingAreaFilter) return props.material.selectedLoadingPointIds.length
  return props.material.selectedLoadingPointIds.filter((id) => {
    const pt = quotationStore.masters.locations.find((p: { id: string; area: string }) => p.id === id)
    return pt?.area === props.material.selectedLoadingAreaFilter
  }).length
})

// Selected points grouped by geographical area
const selectedPointsByArea = computed(() => {
  const map: Record<string, Array<{ id: string; name: string }>> = {}
  props.material.selectedLoadingPointIds.forEach((pid) => {
    const pt = quotationStore.masters.locations.find((p: { id: string; area: string; name: string }) => p.id === pid)
    if (pt) {
      const areaKey = pt.area || 'Unspecified Area'
      if (!map[areaKey]) map[areaKey] = []
      map[areaKey].push({ id: pt.id, name: pt.name })
    }
  })
  return map
})

// Selected destination objects
const selectedDestinationObjects = computed(() => {
  return props.material.selectedDestinationIds
    .map((did) => quotationStore.masters.destinations.find((d: { id: string }) => d.id === did))
    .filter((d): d is { id: string; name: string; emirate: string; zone?: string } => Boolean(d))
})

// Badges calculation
const isComplete = computed(() => {
  return (
    props.material.selectedLoadingPointIds.length > 0 &&
    props.material.selectedDestinationIds.length > 0 &&
    (props.material.rateGroups.length > 0 || !!props.material.quickRate)
  )
})

const rateRangeText = computed(() => {
  if (props.material.rateGroups.length > 0) {
    const rates = props.material.rateGroups.map((rg) => rg.rate)
    const min = Math.min(...rates)
    const max = Math.max(...rates)
    return min === max ? `AED ${min}/TON` : `AED ${min}–${max}/TON`
  }
  if (props.material.quickRate) {
    return `AED ${props.material.quickRate.rate}/TON`
  }
  return null
})

function togglePoint(pointId: string) {
  quotationStore.toggleLoadingPoint(props.index, pointId)
}

function handleSelectAllInArea() {
  if (!props.material.selectedLoadingAreaFilter) return
  quotationStore.selectAllInArea(props.index, props.material.selectedLoadingAreaFilter)
}

function removePoint(pointId: string) {
  quotationStore.toggleLoadingPoint(props.index, pointId)
}

function removeDestination(destId: string) {
  quotationStore.toggleDestination(props.index, destId)
}

function onDestinationsChanged(newDestIds: string | string[]) {
  props.material.selectedDestinationIds = Array.isArray(newDestIds) ? newDestIds : [newDestIds]
}

function toggleExpand() {
  props.material.isExpanded = !props.material.isExpanded
}
</script>

<template>
  <div class="bg-white rounded-xl border border-slate-200/90 shadow-xs transition-all duration-200 overflow-hidden">
    <!-- Card Header -->
    <div
      class="bg-slate-50/50 border-b border-slate-100 p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer select-none transition"
      @click="toggleExpand"
    >
      <div class="flex items-center gap-3.5">
        <div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-200/60 shadow-2xs">
          <Box class="w-5 h-5" />
        </div>
        <div>
          <div class="flex items-center gap-2.5">
            <h3 class="font-bold text-slate-900 text-base">
              {{ material.materialName }}
            </h3>
            <span class="text-xs text-slate-500 font-mono">
              Cargo Type · {{ material.cargoType }}
            </span>
            <span
              v-if="!material.isExpanded"
              class="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 uppercase tracking-wider"
            >
              MATERIAL {{ index + 1 }}
            </span>
          </div>

          <!-- Summary Badges -->
          <div class="flex flex-wrap items-center gap-2 mt-1.5 text-xs">
            <span
              v-if="material.selectedLoadingPointIds.length > 0"
              class="px-2.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 font-medium border border-slate-200/80"
            >
              {{ material.selectedLoadingPointIds.length }} loading points
            </span>
            <span
              v-if="material.selectedDestinationIds.length > 0"
              class="px-2.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 font-medium border border-slate-200/80"
            >
              {{ material.selectedDestinationIds.length }} destinations
            </span>
            <span
              v-if="material.rateGroups.length > 0"
              class="px-2.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 font-medium border border-slate-200/80"
            >
              {{ material.rateGroups.length }} rate groups
            </span>
            <span
              v-if="rateRangeText"
              class="px-2.5 py-0.5 rounded-lg bg-blue-50 text-blue-700 font-semibold border border-blue-200/80"
            >
              {{ rateRangeText }}
            </span>
            <span
              v-if="isComplete"
              class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold"
            >
              <CheckCircle2 class="w-3.5 h-3.5" />
              <span>Complete</span>
            </span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2 self-end md:self-auto" @click.stop>
        <button
          @click="quotationStore.removeMaterial(index)"
          class="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer"
          title="Remove Material"
        >
          <Trash2 class="w-4 h-4" />
        </button>
        <button
          @click="toggleExpand"
          class="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition cursor-pointer"
        >
          <ChevronUp v-if="material.isExpanded" class="w-4 h-4" />
          <ChevronDown v-else class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Expanded Body -->
    <div v-show="material.isExpanded" class="p-5 sm:p-6 space-y-6">
      <!-- Section: Loading Points -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <label class="text-xs font-bold uppercase tracking-wider text-slate-500">
            LOADING POINTS
          </label>
        </div>

        <!-- Filter and Search Row -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-xs font-semibold text-slate-500 mb-1.5 uppercase">
              Loading Area — optional filter
            </label>
            <select
              v-model="material.selectedLoadingAreaFilter"
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs transition hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            >
              <option v-for="area in areaOptions" :key="area.value" :value="area.value">
                {{ area.text }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1.5 uppercase">
              Loading Points <span class="text-rose-500 ml-0.5">*</span>
            </label>
            <div class="relative">
              <input
                type="text"
                v-model="searchQuery"
                placeholder="Search loading points across all areas..."
                class="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-8 text-sm text-slate-900 placeholder:text-slate-400 shadow-xs transition hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
              />
              <Search class="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <button
                v-if="searchQuery"
                type="button"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 rounded-full cursor-pointer"
                title="Clear search"
                @click="searchQuery = ''"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        <!-- Two column point selection panel -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50/50 p-4 rounded-xl border border-slate-200">
          <!-- Left Column: Checkbox point list -->
          <div>
            <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-200">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-slate-900">
                  <template v-if="material.selectedLoadingAreaFilter">
                    {{ material.selectedLoadingAreaFilter }}
                  </template>
                  <template v-else>
                    All Loading Points
                  </template>
                </span>
                <span class="text-[11px] font-bold text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded-md shadow-2xs">
                  {{ selectedInAreaCount }} of {{ pointsInSelectedAreaCount }}
                </span>
              </div>
              <button
                v-if="filteredLoadingPoints.length > 0"
                type="button"
                @click="handleToggleSelectFiltered"
                class="text-xs font-semibold text-blue-600 hover:text-blue-700 transition cursor-pointer"
              >
                {{ allFilteredSelected ? 'Deselect Filtered' : 'Select Filtered' }}
              </button>
            </div>

            <div class="space-y-1 max-h-56 overflow-y-auto pr-1">
              <label
                v-for="point in filteredLoadingPoints"
                :key="point.id"
                class="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-white transition cursor-pointer border border-transparent hover:border-slate-200 group"
              >
                <div class="flex items-center gap-2.5 min-w-0">
                  <input
                    type="checkbox"
                    :checked="material.selectedLoadingPointIds.includes(point.id)"
                    @change="togglePoint(point.id)"
                    class="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500/20 cursor-pointer shrink-0"
                  />
                  <div class="min-w-0">
                    <span class="text-sm font-medium text-slate-900 group-hover:text-blue-700 truncate block">
                      {{ point.name }}
                    </span>
                    <span v-if="point.address" dir="rtl" class="text-[11px] text-slate-400 font-normal truncate block text-right">
                      {{ point.address }}
                    </span>
                  </div>
                </div>
                <span class="text-xs font-mono text-slate-400 group-hover:text-slate-600 shrink-0 ml-2">
                  {{ point.area }}
                </span>
              </label>

              <div v-if="filteredLoadingPoints.length === 0" class="text-xs text-slate-400 py-6 text-center">
                No loading points match your search or filter.
              </div>
            </div>

            <div v-if="material.selectedLoadingAreaFilter && pointsInSelectedAreaCount > 0" class="mt-2.5 pt-2 border-t border-slate-200">
              <button
                @click="handleSelectAllInArea"
                class="text-xs font-medium text-blue-600 hover:text-blue-700 transition cursor-pointer"
              >
                {{ selectedInAreaCount === pointsInSelectedAreaCount ? 'Deselect all in this area' : 'Select all points in this area' }}
              </button>
            </div>
          </div>

          <!-- Right Column: Grouped selected chips & Auto-detect alert -->
          <div class="flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-200">
                <span class="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                  SELECTED · {{ material.selectedLoadingPointIds.length }} LOADING POINTS
                </span>
                <button
                  v-if="material.selectedLoadingPointIds.length > 0"
                  type="button"
                  @click="material.selectedLoadingPointIds = []"
                  class="text-xs font-semibold text-rose-600 hover:text-rose-700 transition cursor-pointer"
                >
                  Clear all
                </button>
              </div>

              <div v-if="material.selectedLoadingPointIds.length === 0" class="text-xs text-slate-400 italic py-6 text-center">
                No loading points selected yet. Pick points from the left list.
              </div>

              <div v-else class="bg-slate-50/70 rounded-lg border border-slate-200/80 p-3 space-y-2.5 max-h-48 overflow-y-auto pr-1">
                <div
                  v-for="(points, areaName) in selectedPointsByArea"
                  :key="areaName"
                  class="bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-2xs"
                >
                  <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center justify-between">
                    <span>{{ areaName }}</span>
                    <span class="text-slate-400 font-mono text-xs">{{ points.length }}</span>
                  </div>
                  <div class="flex flex-wrap gap-1.5">
                    <span
                      v-for="pt in points"
                      :key="pt.id"
                      class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200/70"
                    >
                      <span>{{ pt.name }}</span>
                      <button
                        type="button"
                        @click="removePoint(pt.id)"
                        class="text-blue-500 hover:text-blue-800 transition cursor-pointer"
                      >
                        <X class="w-3.5 h-3.5" />
                      </button>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Auto-detect banner -->
            <div class="mt-4 px-3 py-2 bg-blue-50/60 rounded-lg border border-blue-200/60 flex items-center gap-2 text-xs text-blue-700">
              <Info class="w-4 h-4 text-blue-600 shrink-0" />
              <span class="truncate">
                Area is auto-detected from each selected loading point — no duplicate area entry needed.
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Section: Delivery Destinations -->
      <div class="pt-4 border-t border-slate-200">
        <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
          DELIVERY DESTINATIONS
        </label>

        <div class="space-y-3">
          <div v-if="selectedDestinationObjects.length > 0" class="flex flex-wrap gap-2 items-center">
            <span
              v-for="dest in selectedDestinationObjects"
              :key="dest.id"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200/80 shadow-2xs"
            >
              <MapPin class="w-3.5 h-3.5 text-emerald-600" />
              <span>{{ dest.name }}</span>
              <button
                type="button"
                @click="removeDestination(dest.id)"
                class="text-emerald-500 hover:text-emerald-900 ml-0.5 transition cursor-pointer"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </span>
          </div>

          <!-- MasterSelect for Adding Delivery Destinations -->
          <div class="max-w-xl">
            <MasterSelect
              :model-value="material.selectedDestinationIds"
              :options="destinationOptions"
              :multiple="true"
              :max-options="7"
              doctype="Location"
              placeholder="+ Search and add delivery destinations..."
              :show-refresh="false"
              @update:model-value="onDestinationsChanged"
            />
          </div>
        </div>
      </div>

      <!-- Single Rate Quick Fields -->
      <div
        v-if="material.quickRate"
        class="pt-4 border-t border-slate-200 bg-slate-50/50 p-4 rounded-xl border border-slate-200"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-900">Quick Single Rate</span>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 uppercase">
              SINGLE RATE
            </span>
          </div>
          <button
            @click="delete material.quickRate"
            class="text-xs text-slate-500 hover:text-slate-900 cursor-pointer"
          >
            Switch to Multi-Rate Schedule
          </button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-500 mb-1">RATE</label>
            <div class="relative">
              <input
                type="number"
                step="0.01"
                v-model.number="material.quickRate.rate"
                class="h-10 w-full rounded-lg border border-slate-300 bg-white pr-16 pl-3 text-sm font-semibold text-slate-900 shadow-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
              />
              <span class="absolute right-3 top-2.5 text-xs font-medium text-slate-400">
                AED/TON
              </span>
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 mb-1">EFFECTIVE FROM</label>
            <input
              type="date"
              v-model="material.quickRate.effectiveFrom"
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 mb-1">EFFECTIVE TO</label>
            <input
              type="date"
              v-model="material.quickRate.effectiveTo"
              class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>