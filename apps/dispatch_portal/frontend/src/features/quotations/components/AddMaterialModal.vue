<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Box, Check, ExternalLink, Plus, Search, X } from 'lucide-vue-next'
import { useQuotationFormStore } from '../stores/quotationForm'
import { useDebounce } from '@/composables/useDebounce'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const quotationStore = useQuotationFormStore()
const searchQuery = ref('')
const debouncedSearchQuery = useDebounce(searchQuery, 300)

const filteredMaterials = computed(() => {
  const query = debouncedSearchQuery.value.trim().toLowerCase()
  if (!query) return quotationStore.materialOptions
  return quotationStore.materialOptions.filter((mat) => {
    return (
      mat.name.toLowerCase().includes(query) ||
      mat.code.toLowerCase().includes(query) ||
      (mat.cargoType && mat.cargoType.toLowerCase().includes(query))
    )
  })
})

function selectMaterial(matId: string) {
  quotationStore.addMaterial(matId)
  emit('close')
}

function isAlreadyAdded(matId: string) {
  return quotationStore.quotation.materials.some((m: { materialId: string }) => m.materialId === matId)
}

function openCreateMaterialInERPNext() {
  const query = searchQuery.value.trim()
  const url = query
    ? `/desk/cargo-types/new?cargo_name=${encodeURIComponent(query)}`
    : '/desk/cargo-types/new'
  window.open(url, '_blank')
}

function onWindowFocus() {
  if (props.open) {
    void quotationStore.loadMasters()
  }
}

onMounted(() => {
  window.addEventListener('focus', onWindowFocus)
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', onWindowFocus)
})
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto"
  >
    <div class="relative bg-card rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-border">
      <div class="px-6 py-4 bg-[#001233] text-white flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <Box class="size-5 text-primary" />
          <h3 class="text-base font-bold">Select Material</h3>
        </div>
        <button
          @click="$emit('close')"
          class="p-1.5 text-slate-400 hover:text-white rounded-lg transition cursor-pointer"
          aria-label="Close dialog"
        >
          <X class="size-5" />
        </button>
      </div>

      <div class="p-6 space-y-3">
        <p class="text-xs text-muted-foreground mb-1">
          Choose a material from the bulk material catalog to add to this quotation.
        </p>

        <!-- Search Bar -->
        <div class="relative">
          <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Search materials by name or code…"
            class="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-8 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/15 focus:border-blue-600 transition shadow-xs"
          />
          <button
            v-if="searchQuery"
            type="button"
            class="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 rounded-full cursor-pointer"
            title="Clear search"
            @click="searchQuery = ''"
          >
            <X class="size-3.5" />
          </button>
        </div>

        <div class="space-y-2 max-h-80 overflow-y-auto pr-1">
          <div
            v-for="mat in filteredMaterials"
            :key="mat.id"
            @click="!isAlreadyAdded(mat.id) && selectMaterial(mat.id)"
            :class="[
              'p-3.5 rounded-lg border flex items-center justify-between transition',
              isAlreadyAdded(mat.id)
                ? 'bg-slate-50 border-slate-200 opacity-60 cursor-not-allowed'
                : 'bg-white border-slate-200 hover:border-blue-600 hover:bg-blue-50/30 cursor-pointer shadow-2xs'
            ]"
          >
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center shrink-0 border border-blue-200/60 font-bold text-xs">
                {{ mat.code.slice(0, 3) }}
              </div>
              <div>
                <div class="text-sm font-bold text-slate-900">{{ mat.name }}</div>
                <div class="text-xs text-slate-500 font-mono">
                  Cargo Code: {{ mat.code }} · UOM: {{ mat.uom }}
                </div>
              </div>
            </div>

            <div>
              <span
                v-if="isAlreadyAdded(mat.id)"
                class="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-md"
              >
                <Check class="size-3" />
                <span>Added</span>
              </span>
              <button
                v-else
                type="button"
                class="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200/80 px-3 py-1 rounded-lg transition cursor-pointer"
              >
                <Plus class="size-3" />
                <span>Select</span>
              </button>
            </div>
          </div>

          <!-- Empty State with ERPNext Material Creation Link -->
          <div v-if="filteredMaterials.length === 0" class="py-8 text-center">
            <p class="text-sm font-semibold text-foreground mb-1">No matching materials found</p>
            <p class="text-xs text-muted-foreground mb-4">
              No material matches "{{ searchQuery }}". You can create it in ERPNext Materials.
            </p>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow-xs transition-all hover:bg-primary/90 cursor-pointer"
              @click="openCreateMaterialInERPNext"
            >
              <span>+ Create "{{ searchQuery }}" in ERPNext Materials</span>
              <ExternalLink class="size-3" />
            </button>
          </div>
        </div>
      </div>

      <div class="px-6 py-3.5 bg-muted/30 border-t border-border flex items-center justify-between">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline cursor-pointer"
          @click="openCreateMaterialInERPNext"
        >
          <span>+ Create new Material in ERPNext</span>
          <ExternalLink class="size-3" />
        </button>

        <button
          @click="$emit('close')"
          class="px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted rounded-lg transition cursor-pointer"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>