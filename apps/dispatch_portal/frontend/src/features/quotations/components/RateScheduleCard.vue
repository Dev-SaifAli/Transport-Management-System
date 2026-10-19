<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuotationFormStore } from '../stores/quotationForm'
import type { RateGroup } from '../types'
import {
  Coins,
  Plus,
  Trash2,
  Copy,
  ChevronDown,
  ChevronUp,
  MapPin,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  X,
} from 'lucide-vue-next'

const quotationStore = useQuotationFormStore()

const isExpanded = ref(true)
const activeGroupIdx = ref<number>(0)
const showAddPointDropdown = ref<number | null>(null)

// Get currently selected material for detailed rate groups
const targetMaterial = computed(() => {
  if (quotationStore.quotation.materials.length === 0) return null
  const found = quotationStore.quotation.materials.find(
    (m: { id: string }) => m.id === quotationStore.activeRateGroupMaterialId
  )
  return found || quotationStore.quotation.materials[0]
})

const targetMaterialIndex = computed(() => {
  if (!targetMaterial.value) return -1
  return quotationStore.quotation.materials.findIndex((m: { id: string }) => m.id === targetMaterial.value?.id)
})

const isUnlocked = computed(() => {
  return quotationStore.quotation.materials.some(
    (m: { selectedLoadingPointIds: string[]; selectedDestinationIds: string[] }) => m.selectedLoadingPointIds.length > 0 && m.selectedDestinationIds.length > 0
  )
})

// Destination options for rate groups
const destinationOptions = computed(() => {
  if (!targetMaterial.value) return []
  // Prefer material's chosen destinations, or all destinations
  const materialDests = targetMaterial.value.selectedDestinationIds
    .map((did: string) => quotationStore.masters.destinations.find((d: { id: string }) => d.id === did))
    .filter(Boolean)

  if (materialDests.length > 0) return materialDests
  return quotationStore.masters.destinations
})

function getPointName(pointId: string) {
  const p = quotationStore.masters.locations.find((pt: { id: string }) => pt.id === pointId)
  return p ? p.name : pointId
}

function getDestName(destId: string) {
  const d = quotationStore.masters.destinations.find((dst: { id: string }) => dst.id === destId)
  return d ? d.name : destId
}

function formatDateShort(dateStr: string) {
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

function handleAddRateGroup() {
  if (targetMaterialIndex.value >= 0) {
    quotationStore.addRateGroup(targetMaterialIndex.value)
    activeGroupIdx.value = (targetMaterial.value?.rateGroups.length || 1) - 1
  }
}

function handleRemovePointFromGroup(group: RateGroup, pointId: string) {
  group.loadingPointIds = group.loadingPointIds.filter((id) => id !== pointId)
  group.isShared = group.loadingPointIds.length > 1
}

function handleAddPointToGroup(group: RateGroup, pointId: string) {
  if (!group.loadingPointIds.includes(pointId)) {
    group.loadingPointIds.push(pointId)
    group.isShared = group.loadingPointIds.length > 1
  }
  showAddPointDropdown.value = null
}

// Loading points of this material that are not yet in the specified group
function getAvailablePointsForGroup(group: RateGroup) {
  if (!targetMaterial.value) return []
  return targetMaterial.value.selectedLoadingPointIds
    .filter((id: string) => !group.loadingPointIds.includes(id))
    .map((id: string) => quotationStore.masters.locations.find((p: { id: string }) => p.id === id))
    .filter((p): p is { id: string; name: string; area: string } => Boolean(p))
}
</script>

<template>
  <div class="bg-card rounded-xl border border-border/90 shadow-sm transition-all duration-200 overflow-hidden">
    <!-- Header banner -->
    <div
      class="p-4 sm:p-5 flex items-center justify-between cursor-pointer select-none bg-card hover:bg-accent/50 transition"
      @click="isExpanded = !isExpanded"
    >
      <div class="flex items-center gap-3.5">
        <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20 shadow-xs">
          <Coins class="w-5 h-5" />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-bold text-foreground text-base">
              Commercial Rate Schedule
            </h3>
            <span
              v-if="!isExpanded"
              class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-muted text-muted-foreground font-mono"
            >
              {{ quotationStore.totalRateGroupsCount }} RATE GROUPS
            </span>
          </div>
          <p class="text-xs text-muted-foreground mt-0.5">
            <template v-if="targetMaterial">
              {{ targetMaterial.materialName }} · shared rate groups and per-point rates · date-wise effective periods
            </template>
            <template v-else>
              Define shared or per-point rates with effective dates
            </template>
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <span
          v-if="!isUnlocked"
          class="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-md hidden sm:inline-flex items-center gap-1.5"
        >
          <AlertCircle class="w-3.5 h-3.5" />
          <span>Unlocks once loading points & destinations are selected</span>
        </span>

        <button
          v-if="isUnlocked && targetMaterial"
          @click.stop="handleAddRateGroup"
          class="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold rounded-lg shadow-xs transition cursor-pointer"
        >
          <Plus class="w-4 h-4" />
          <span>Add Rate Group</span>
        </button>

        <button class="p-1.5 text-muted-foreground hover:text-foreground rounded-lg transition">
          <ChevronUp v-if="isExpanded" class="w-5 h-5" />
          <ChevronDown v-else class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- Rate Schedule Content -->
    <div v-show="isExpanded" class="border-t border-border p-5 sm:p-6 space-y-6">
      <!-- Locked Banner if no points/destinations selected yet -->
      <div
        v-if="!isUnlocked"
        class="bg-muted/30 p-6 rounded-xl border border-dashed border-border text-center space-y-2"
      >
        <Coins class="w-8 h-8 text-muted-foreground mx-auto" />
        <p class="text-sm font-semibold text-foreground">
          The Commercial Rate Schedule unlocks once loading points and destinations are selected.
        </p>
        <p class="text-xs text-muted-foreground max-w-md mx-auto">
          Add at least one transportation material with loading points and delivery destinations above to build price schedules.
        </p>
      </div>

      <!-- When Unlocked -->
      <div v-else class="space-y-6">
        <!-- Material Selector Tabs if multiple materials exist -->
        <div v-if="quotationStore.quotation.materials.length > 1" class="flex items-center gap-2 border-b border-border pb-2 overflow-x-auto">
          <span class="text-xs font-semibold text-muted-foreground uppercase mr-1">Configure Material:</span>
          <button
            v-for="m in quotationStore.quotation.materials"
            :key="m.id"
            @click="quotationStore.activeRateGroupMaterialId = m.id"
            :class="[
              'px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-2',
              targetMaterial?.id === m.id
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'bg-muted text-foreground hover:bg-muted/80'
            ]"
          >
            <span>{{ m.materialName }}</span>
            <span class="text-[10px] px-1.5 py-0.2 rounded bg-white/20 font-mono">
              {{ m.rateGroups.length }}
            </span>
          </button>
        </div>

        <!-- Active Material Rate Group Configuration -->
        <div v-if="targetMaterial && targetMaterial.rateGroups.length > 0" class="space-y-6">
          <div
            v-for="(rg, gIdx) in targetMaterial.rateGroups"
            :key="rg.id"
            class="border rounded-xl transition-all duration-200 overflow-hidden shadow-xs"
            :class="[
              activeGroupIdx === gIdx
                ? 'border-primary ring-2 ring-primary/10 bg-card'
                : 'border-border bg-card'
            ]"
          >
            <!-- Rate Group Header -->
            <div class="px-5 py-3.5 bg-muted/50 border-b border-border flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center gap-3">
                <span class="font-bold text-foreground text-sm sm:text-base">
                  {{ rg.name }}
                </span>
                <span
                  :class="[
                    'text-[11px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider',
                    rg.isShared
                      ? 'bg-green-50 text-green-700 border border-green-200'
                      : 'bg-muted text-foreground border border-border'
                  ]"
                >
                  {{ rg.isShared ? 'SHARED RATE' : 'SINGLE POINT' }}
                </span>
              </div>

              <div class="flex items-center gap-3">
                <button
                  @click="quotationStore.duplicateRateGroup(targetMaterialIndex, gIdx)"
                  class="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition cursor-pointer"
                >
                  <Copy class="w-3.5 h-3.5 text-muted-foreground" />
                  <span>Duplicate</span>
                </button>
                <button
                  @click="quotationStore.removeRateGroup(targetMaterialIndex, gIdx)"
                  class="inline-flex items-center gap-1.5 text-xs font-medium text-destructive hover:text-destructive/80 transition cursor-pointer"
                >
                  <Trash2 class="w-3.5 h-3.5 text-destructive" />
                  <span>Remove</span>
                </button>
              </div>
            </div>

            <!-- Rate Group Form and Right Side Preview (Split Panel) -->
            <div class="p-5 grid grid-cols-1 lg:grid-cols-12 gap-6">
              <!-- Left Form Section (7 cols) -->
              <div class="lg:col-span-7 space-y-4">
                <!-- Loading Points chips with + Add point -->
                <div>
                  <div class="flex items-center justify-between mb-1.5">
                    <label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                      LOADING POINTS · {{ rg.loadingPointIds.length }}
                    </label>
                  </div>

                  <div class="flex flex-wrap items-center gap-2">
                    <span
                      v-for="pid in rg.loadingPointIds"
                      :key="pid"
                      class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                    >
                      <span>{{ getPointName(pid) }}</span>
                      <button
                        @click="handleRemovePointFromGroup(rg, pid)"
                        class="text-primary/70 hover:text-primary transition cursor-pointer"
                        title="Remove point from group"
                      >
                        <X class="w-3.5 h-3.5" />
                      </button>
                    </span>

                    <!-- Add point popover button -->
                    <div class="relative">
                      <button
                        @click="showAddPointDropdown = showAddPointDropdown === gIdx ? null : gIdx"
                        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium border border-dashed border-border text-muted-foreground hover:text-primary hover:border-primary/50 hover:bg-primary/5 transition cursor-pointer"
                      >
                        <Plus class="w-3 h-3" />
                        <span>Add point</span>
                      </button>

                      <!-- Dropdown menu -->
                      <div
                        v-if="showAddPointDropdown === gIdx"
                        class="absolute left-0 mt-1 w-52 bg-card rounded-lg shadow-lg border border-border z-30 py-1"
                      >
                        <div class="text-[10px] font-bold text-muted-foreground uppercase px-3 py-1 border-b border-border">
                          Available Material Points
                        </div>
                        <button
                          v-for="p in getAvailablePointsForGroup(rg)"
                          :key="p?.id"
                          @click="handleAddPointToGroup(rg, p!.id)"
                          class="w-full text-left px-3 py-1.5 text-xs text-foreground hover:bg-primary/5 hover:text-primary transition flex items-center justify-between"
                        >
                          <span>{{ p?.name }}</span>
                          <span class="text-[10px] text-muted-foreground">{{ p?.area }}</span>
                        </button>
                        <div
                          v-if="getAvailablePointsForGroup(rg).length === 0"
                          class="px-3 py-2 text-xs text-muted-foreground italic"
                        >
                          All material points are in this group.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Destination and Rates row -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-semibold text-foreground mb-1">
                      Delivery Destination <span class="text-destructive ml-1">*</span>
                    </label>
                    <select
                      v-model="rg.destinationId"
                      class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
                    >
                      <option v-for="dest in destinationOptions" :key="dest?.id" :value="dest?.id">
                        {{ dest?.name }}
                      </option>
                    </select>
                  </div>

                  <div class="grid grid-cols-2 gap-2">
                    <div>
                      <label class="block text-xs font-semibold text-foreground mb-1">
                        Rate <span class="text-destructive ml-1">*</span>
                      </label>
                      <div class="relative">
                        <input
                          type="number"
                          step="0.01"
                          v-model.number="rg.rate"
                          class="w-full border border-input bg-background text-foreground text-sm font-semibold pl-3 pr-14 py-2 focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
                        />
                        <span class="absolute right-2 top-2 text-[11px] text-muted-foreground font-medium">
                          AED/TON
                        </span>
                      </div>
                    </div>
                    <div>
                      <label class="block text-xs font-semibold text-muted-foreground mb-1">
                        Currency
                      </label>
                      <input
                        type="text"
                        readonly
                        :value="rg.currency"
                        class="w-full bg-muted/40 border border-border rounded-lg px-3 py-2 text-sm text-muted-foreground font-mono focus:outline-none"
                      />
                    </div>
                  </div>
                </div>

                <!-- Effective From / To -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-semibold text-foreground mb-1">
                      Effective From <span class="text-destructive ml-1">*</span>
                    </label>
                    <input
                      type="date"
                      v-model="rg.effectiveFrom"
                      class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-foreground mb-1">
                      Effective To <span class="text-destructive ml-1">*</span>
                    </label>
                    <input
                      type="date"
                      v-model="rg.effectiveTo"
                      class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none transition"
                    />
                  </div>
                </div>

                <!-- Rate Resolution Banner -->
                <div class="p-3 bg-primary/10 rounded-lg border border-primary/20 flex items-start gap-2.5 text-xs text-primary">
                  <CheckCircle2 class="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  <span>
                    {{ rg.isShared ? `All ${rg.loadingPointIds.length} loading points` : 'This loading point' }} receive
                    <strong>{{ rg.currency }} {{ Number(rg.rate).toFixed(2) }}/TON</strong> for
                    {{ formatDateShort(rg.effectiveFrom) }}–{{ formatDateShort(rg.effectiveTo) }}. Individual rate lines are preserved per point.
                  </span>
                </div>
              </div>

              <!-- Right Preview Section (5 cols) -->
              <div class="lg:col-span-5 bg-muted/30 p-4 rounded-xl border border-border flex flex-col justify-between">
                <div>
                  <div class="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                    Rate lines created by this group
                  </div>

                  <div class="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                    <div
                      v-for="pid in rg.loadingPointIds"
                      :key="pid"
                      class="bg-card p-3 rounded-lg border border-border shadow-2xs flex items-center justify-between gap-3"
                    >
                      <div class="flex items-start gap-2.5">
                        <MapPin class="w-4 h-4 text-primary shrink-0 mt-0.5" />
                        <div>
                          <div class="text-xs font-bold text-foreground flex items-center gap-1.5">
                            <span>{{ getPointName(pid) }}</span>
                            <ArrowRight class="w-3 h-3 text-muted-foreground" />
                            <span>{{ getDestName(rg.destinationId) }}</span>
                          </div>
                          <div class="text-[11px] text-muted-foreground mt-0.5">
                            {{ rg.currency }} {{ Number(rg.rate).toFixed(2) }}/TON · {{ formatDateShort(rg.effectiveFrom) }}–{{ formatDateShort(rg.effectiveTo) }}
                          </div>
                        </div>
                      </div>

                      <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-100 text-green-800 shrink-0">
                        NEW
                      </span>
                    </div>

                    <div v-if="rg.loadingPointIds.length === 0" class="text-xs text-muted-foreground italic py-4 text-center">
                      No loading points selected for this group yet.
                    </div>
                  </div>
                </div>

                <p class="text-[11px] text-muted-foreground mt-4 pt-3 border-t border-border leading-relaxed">
                  Shared groups are a fast way to price many points at once — billing always resolves the exact rate of the actual loading point.
                </p>
              </div>
            </div>
          </div>

          <!-- Add another rate group dashed button -->
          <button
            @click="handleAddRateGroup"
            class="w-full py-3.5 border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 rounded-xl text-xs font-bold text-primary flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <Plus class="w-4 h-4" />
            <span>Add Rate Group</span>
          </button>
        </div>

        <div v-else class="text-center py-8">
          <p class="text-xs text-muted-foreground mb-3">No rate groups created yet for this material.</p>
          <button
            @click="handleAddRateGroup"
            class="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-xs font-semibold hover:bg-primary/90 transition cursor-pointer"
          >
            <Plus class="w-4 h-4" />
            <span>Create First Rate Group</span>
          </button>
        </div>

        <!-- Commercial Rate Schedule — Preview Table -->
        <div v-if="quotationStore.allRateLines.length > 0" class="pt-6 border-t border-border">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-xs font-bold uppercase tracking-wider text-foreground">
              Commercial Rate Schedule — preview
            </h4>
            <span class="text-xs text-muted-foreground font-mono">
              {{ quotationStore.allRateLines.length }} total rate lines
            </span>
          </div>

          <div class="overflow-x-auto rounded-xl border border-border">
            <table class="w-full text-left border-collapse text-xs">
              <thead>
                <tr class="bg-muted/50 text-muted-foreground uppercase tracking-wider text-[11px] border-b border-border">
                  <th class="py-3 px-4 font-bold">MATERIAL</th>
                  <th class="py-3 px-4 font-bold">LOADING POINTS</th>
                  <th class="py-3 px-4 font-bold">DESTINATION</th>
                  <th class="py-3 px-4 font-bold">RATE</th>
                  <th class="py-3 px-4 font-bold">EFFECTIVE</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border bg-card">
                <tr
                  v-for="(line, idx) in quotationStore.allRateLines"
                  :key="idx"
                  class="hover:bg-muted/30 transition"
                >
                  <td class="py-3 px-4 font-semibold text-foreground">
                    {{ line.materialName }}
                  </td>
                  <td class="py-3 px-4 text-foreground font-medium">
                    {{ line.loadingPointsNames }}
                  </td>
                  <td class="py-3 px-4 text-foreground">
                    {{ line.destinationName }}
                  </td>
                  <td class="py-3 px-4 font-bold text-foreground">
                    {{ line.currency }} {{ Number(line.rate).toFixed(2) }}
                  </td>
                  <td class="py-3 px-4 text-muted-foreground font-mono text-[11px]">
                    {{ line.effectiveText }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>