<script setup lang="ts">
import { useQuotationFormStore } from '../stores/quotationForm'
import { Box, X, Plus, Check } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const quotationStore = useQuotationFormStore()

function selectMaterial(matId: string) {
  quotationStore.addMaterial(matId)
  emit('close')
}

function isAlreadyAdded(matId: string) {
  return quotationStore.quotation.materials.some((m: { materialId: string }) => m.materialId === matId)
}
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto"
  >
    <div class="relative bg-card rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-border">
      <div class="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <Box class="w-5 h-5 text-primary" />
          <h3 class="text-base font-bold">Select Cargo Material</h3>
        </div>
        <button
          @click="$emit('close')"
          class="p-1.5 text-slate-400 hover:text-white rounded-lg transition cursor-pointer"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <div class="p-6 space-y-3">
        <p class="text-xs text-muted-foreground mb-2">
          Choose a material item from the ERPNext bulk cargo catalog to add to this quotation.
        </p>

        <div class="space-y-2 max-h-80 overflow-y-auto pr-1">
          <div
            v-for="mat in quotationStore.materialOptions"
            :key="mat.id"
            @click="!isAlreadyAdded(mat.id) && selectMaterial(mat.id)"
            :class="[
              'p-3.5 rounded-xl border flex items-center justify-between transition',
              isAlreadyAdded(mat.id)
                ? 'bg-muted/30 border-border opacity-60 cursor-not-allowed'
                : 'bg-card border-border hover:border-primary hover:bg-primary/5 cursor-pointer shadow-2xs'
            ]"
          >
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20 font-bold text-xs">
                {{ mat.code.slice(0, 3) }}
              </div>
              <div>
                <div class="text-sm font-bold text-foreground">{{ mat.name }}</div>
                <div class="text-xs text-muted-foreground font-mono">
                  Cargo Code: {{ mat.code }} · UOM: {{ mat.uom }}
                </div>
              </div>
            </div>

            <div>
              <span
                v-if="isAlreadyAdded(mat.id)"
                class="inline-flex items-center gap-1 text-[11px] font-semibold text-green-700 bg-green-50 border border-green-200 px-2.5 py-0.5 rounded-full"
              >
                <Check class="w-3 h-3" />
                <span>Added</span>
              </span>
              <button
                v-else
                class="inline-flex items-center gap-1 text-xs font-semibold text-primary bg-primary/10 hover:bg-primary/20 border border-primary/20 px-3 py-1 rounded-lg transition"
              >
                <Plus class="w-3 h-3" />
                <span>Select</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="px-6 py-3.5 bg-muted/30 border-t border-border flex justify-end">
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