<script setup lang="ts">
import { computed, ref } from 'vue'
import type { QuotationMaterial } from '../types'
import { useQuotationFormStore } from '../stores/quotationForm'
import TomSelect from './TomSelect.vue'
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

// Filtered loading points for the checkbox list
const filteredLoadingPoints = computed(() => {
  return quotationStore.masters.locations.filter((point: { name: string; area: string }) => {
    const matchesArea = !props.material.selectedLoadingAreaFilter || point.area === props.material.selectedLoadingAreaFilter
    const matchesSearch = !searchQuery.value || point.name.toLowerCase().includes(searchQuery.value.toLowerCase()) || point.area.toLowerCase().includes(searchQuery.value.toLowerCase())
    return matchesArea && matchesSearch
  })
})

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
  <div class="bg-card rounded-xl border border-border/90 shadow-sm transition-all duration-200 overflow-hidden">
    <!-- Card Header -->
    <div
      class="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer select-none bg-card hover:bg-accent/50 transition"
      @click="toggleExpand"
    >
      <div class="flex items-center gap-3.5">
        <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20 shadow-xs">
          <Box class="w-5 h-5" />
        </div>
        <div>
          <div class="flex items-center gap-2.5">
            <h3 class="font-bold text-foreground text-base">
              {{ material.materialName }}
            </h3>
            <span class="text-xs text-muted-foreground font-mono">
              Cargo Type · {{ material.cargoType }}
            </span>
            <span
              v-if="!material.isExpanded"
              class="text-[11px] font-semibold px-2 py-0.5 rounded bg-muted text-muted-foreground uppercase tracking-wider"
            >
              MATERIAL {{ index + 1 }}
            </span>
          </div>

          <!-- Summary Badges -->
          <div class="flex flex-wrap items-center gap-2 mt-1.5 text-xs">
            <span
              v-if="material.selectedLoadingPointIds.length > 0"
              class="px-2.5 py-0.5 rounded-full bg-muted text-foreground font-medium"
            >
              {{ material.selectedLoadingPointIds.length }} loading points
            </span>
            <span
              v-if="material.selectedDestinationIds.length > 0"
              class="px-2.5 py-0.5 rounded-full bg-muted text-foreground font-medium"
            >
              {{ material.selectedDestinationIds.length }} destinations
            </span>
            <span
              v-if="material.rateGroups.length > 0"
              class="px-2.5 py-0.5 rounded-full bg-muted text-foreground font-medium"
            >
              {{ material.rateGroups.length }} rate groups
            </span>
            <span
              v-if="rateRangeText"
              class="px-2.5 py-0.5 rounded-full bg-primary/10 text-primary font-semibold border border-primary/20"
            >
              {{ rateRangeText }}
            </span>
            <span
              v-if="isComplete"
              class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200 font-semibold"
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
          class="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition cursor-pointer"
          title="Remove Material"
        >
          <Trash2 class="w-4 h-4" />
        </button>
        <button
          @click="toggleExpand"
          class="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition cursor-pointer"
        >
          <ChevronUp v-if="material.isExpanded" class="w-4 h-4" />
          <ChevronDown v-else class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Expanded Body -->
    <div v-show="material.isExpanded" class="border-t border-border p-5 sm:p-6 space-y-6">
      <!-- Section: Loading Points -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            LOADING POINTS
          </label>
        </div>

        <!-- Filter and Search Row -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-xs font-semibold text-muted-foreground mb-1.5 uppercase">
              Loading Area — optional filter
            </label>
            <select
              v-model="material.selectedLoadingAreaFilter"
              class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
            >
              <option v-for="area in areaOptions" :key="area.value" :value="area.value">
                {{ area.text }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-foreground mb-1.5 uppercase">
              Loading Points <span class="text-destructive ml-1">*</span>
            </label>
            <div class="relative">
              <input
                type="text"
                v-model="searchQuery"
                placeholder="Search loading points across all areas..."
                class="w-full pl-9 pr-3 py-2 border border-input bg-background text-foreground text-sm rounded-lg placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
              />
              <Search class="w-4 h-4 text-muted-foreground absolute left-3 top-2.5" />
            </div>
          </div>
        </div>

        <!-- Two column point selection panel -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 bg-muted/30 p-4 rounded-xl border border-border">
          <!-- Left Column: Checkbox point list -->
          <div>
            <div class="flex items-center justify-between pb-2 mb-2 border-b border-border">
              <span class="text-xs font-semibold text-foreground">
                <template v-if="material.selectedLoadingAreaFilter">
                  Loading points in {{ material.selectedLoadingAreaFilter }}
                </template>
                <template v-else>
                  All Loading Points
                </template>
              </span>
              <span class="text-xs font-bold text-muted-foreground bg-card border border-border px-2 py-0.5 rounded-md">
                {{ selectedInAreaCount }} of {{ pointsInSelectedAreaCount }}
              </span>
            </div>

            <div class="space-y-1.5 max-h-56 overflow-y-auto pr-1">
              <label
                v-for="point in filteredLoadingPoints"
                :key="point.id"
                class="flex items-center justify-between p-2 rounded-lg hover:bg-card transition cursor-pointer border border-transparent hover:border-border group"
              >
                <div class="flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    :checked="material.selectedLoadingPointIds.includes(point.id)"
                    @change="togglePoint(point.id)"
                    class="w-4 h-4 text-primary rounded border-input focus:ring-primary cursor-pointer"
                  />
                  <span class="text-sm font-medium text-foreground group-hover:text-primary">
                    {{ point.name }}
                  </span>
                </div>
                <span class="text-xs font-mono text-muted-foreground group-hover:text-foreground">
                  {{ point.area }}
                </span>
              </label>

              <div v-if="filteredLoadingPoints.length === 0" class="text-xs text-muted-foreground py-4 text-center">
                No loading points match your search or filter.
              </div>
            </div>

            <div v-if="material.selectedLoadingAreaFilter && pointsInSelectedAreaCount > 0" class="mt-2.5 pt-2 border-t border-border">
              <button
                @click="handleSelectAllInArea"
                class="text-xs font-medium text-primary hover:text-primary/80 transition cursor-pointer"
              >
                {{ selectedInAreaCount === pointsInSelectedAreaCount ? 'Deselect all in this area' : 'Select all points in this area' }}
              </button>
            </div>
          </div>

          <!-- Right Column: Grouped selected chips & Auto-detect alert -->
          <div class="flex flex-col justify-between">
            <div>
              <div class="text-xs font-semibold text-foreground uppercase tracking-wider mb-2.5">
                SELECTED · {{ material.selectedLoadingPointIds.length }} LOADING POINTS
              </div>

              <div v-if="material.selectedLoadingPointIds.length === 0" class="text-xs text-muted-foreground italic py-6 text-center">
                No loading points selected yet. Pick points from the left list.
              </div>

              <div v-else class="space-y-3 max-h-48 overflow-y-auto pr-1">
                <div
                  v-for="(points, areaName) in selectedPointsByArea"
                  :key="areaName"
                  class="bg-card p-2.5 rounded-lg border border-border shadow-2xs"
                >
                  <div class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5 flex items-center justify-between">
                    <span>{{ areaName }}</span>
                    <span class="text-muted-foreground font-mono">{{ points.length }}</span>
                  </div>
                  <div class="flex flex-wrap gap-1.5">
                    <span
                      v-for="pt in points"
                      :key="pt.id"
                      class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                    >
                      <span>{{ pt.name }}</span>
                      <button
                        @click="removePoint(pt.id)"
                        class="text-primary/70 hover:text-primary transition cursor-pointer"
                      >
                        <X class="w-3.5 h-3.5" />
                      </button>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Auto-detect banner -->
            <div class="mt-4 p-3 bg-primary/10 rounded-lg border border-primary/20 flex items-start gap-2.5 text-xs text-primary">
              <Info class="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <span>
                Area is auto-detected from each selected loading point — no duplicate area entry needed. Changing or clearing the area filter never removes already selected loading points.
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Section: Delivery Destinations -->
      <div class="pt-4 border-t border-border">
        <label class="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
          DELIVERY DESTINATIONS
        </label>

        <div class="space-y-3">
          <div class="flex flex-wrap gap-2 items-center">
            <span
              v-for="dest in selectedDestinationObjects"
              :key="dest.id"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-green-50 text-green-800 border border-green-200 shadow-2xs"
            >
              <MapPin class="w-3 h-3 text-green-600" />
              <span>{{ dest.name }}</span>
              <button
                @click="removeDestination(dest.id)"
                class="text-green-500 hover:text-green-900 ml-0.5 transition cursor-pointer"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </span>
          </div>

          <!-- TomSelect for Adding Delivery Destinations -->
          <div class="max-w-xl">
            <TomSelect
              :model-value="material.selectedDestinationIds"
              :options="destinationOptions"
              :multiple="true"
              placeholder="+ Search and add delivery destinations..."
              @update:model-value="onDestinationsChanged"
            />
          </div>
        </div>
      </div>

      <!-- Single Rate Quick Fields (for quick simple materials like Aggregate in Screenshot 6) -->
      <div
        v-if="material.quickRate"
        class="pt-4 border-t border-border bg-muted/30 p-4 rounded-xl border border-border"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold uppercase tracking-wider text-foreground">Quick Single Rate</span>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-green-100 text-green-800 uppercase">
              SINGLE RATE
            </span>
          </div>
          <button
            @click="delete material.quickRate"
            class="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
          >
            Switch to Multi-Rate Schedule
          </button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs font-semibold text-muted-foreground mb-1">RATE</label>
            <div class="relative">
              <input
                type="number"
                step="0.01"
                v-model.number="material.quickRate.rate"
                class="w-full border border-input bg-background text-foreground text-sm font-semibold pr-16 outline-none focus:border-ring"
              />
              <span class="absolute right-3 top-2.5 text-xs font-medium text-muted-foreground">
                AED/TON
              </span>
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold text-muted-foreground mb-1">EFFECTIVE FROM</label>
            <input
              type="date"
              v-model="material.quickRate.effectiveFrom"
              class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 outline-none focus:border-ring"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold text-muted-foreground mb-1">EFFECTIVE TO</label>
            <input
              type="date"
              v-model="material.quickRate.effectiveTo"
              class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 outline-none focus:border-ring"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>