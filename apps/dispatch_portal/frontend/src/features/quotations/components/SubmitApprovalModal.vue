<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuotationFormStore } from '../stores/quotationForm'
import type { QuotationMaterial } from '../types'
import { CheckCircle2, AlertCircle, X, Send, ShieldCheck, Calendar } from 'lucide-vue-next'

const quotationStore = useQuotationFormStore()

const isSubmitModalOpen = computed(() => quotationStore.submitModalOpen)
const approvalDate = ref('')
const approverNote = ref('Commercial rates aligned with Q4 2026 fleet diesel index. Valid for client review.')

const today = new Date().toISOString().slice(0, 10)

const maxApprovalDate = computed(() => {
  const validUntil = quotationStore.quotation.validUntil
  if (validUntil && validUntil < today) return validUntil
  return today
})

const validationErrors = computed(() => {
  const errors: string[] = []
  if (!quotationStore.quotation.customerId && !quotationStore.quotation.customerName) {
    errors.push('Customer must be selected from ERPNext master')
  }
  if (!quotationStore.quotation.validUntil) {
    errors.push('Valid Until date is required')
  } else if (
    quotationStore.quotation.quotationDate &&
    quotationStore.quotation.validUntil < quotationStore.quotation.quotationDate
  ) {
    errors.push('Valid Until cannot be before the Quotation Date')
  }
  if (quotationStore.quotation.materials.length === 0) {
    errors.push('At least one transportation material is required')
  }
  if (!approvalDate.value) {
    errors.push('Customer Approval Date is required')
  } else {
    if (quotationStore.quotation.quotationDate && approvalDate.value < quotationStore.quotation.quotationDate) {
      errors.push('Customer Approval Date cannot be before the Quotation Date')
    }
    if (quotationStore.quotation.validUntil && approvalDate.value > quotationStore.quotation.validUntil) {
      errors.push('Customer Approval Date cannot be after Acceptance Valid Until')
    }
    if (approvalDate.value > today) {
      errors.push('Customer Approval Date cannot be in the future')
    }
  }
  quotationStore.quotation.materials.forEach((m: QuotationMaterial) => {
    if (m.selectedLoadingPointIds.length === 0) {
      errors.push(m.materialName + ' has no loading points selected')
    }
    if (m.selectedDestinationIds.length === 0) {
      errors.push(m.materialName + ' has no delivery destinations selected')
    }
    if (m.rateGroups.length === 0 && !m.quickRate) {
      errors.push(m.materialName + ' has no rate groups or commercial rates configured')
    }
  })
  return errors
})

const canSubmit = computed(() => validationErrors.value.length === 0)

function handleSubmit() {
  if (!canSubmit.value || quotationStore.isSubmitting) return
  void quotationStore.submitForApproval(approvalDate.value, approverNote.value)
}

function handleCancel() {
  if (quotationStore.isSubmitting) return
  quotationStore.clearModalError()
  quotationStore.submitModalOpen = false
}

function closeOnOverlayClick(e: MouseEvent) {
  if ((e.target as HTMLElement) === e.currentTarget) {
    handleCancel()
  }
}
</script>

<template>
  <div
    v-if="isSubmitModalOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto"
    @click="closeOnOverlayClick"
  >
    <div class="relative bg-card rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-border">
      <div class="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <ShieldCheck class="w-5 h-5 text-green-400" />
          <h3 class="text-base font-bold">Record Customer Approval</h3>
        </div>
        <button
          @click="handleCancel"
          :disabled="quotationStore.isSubmitting"
          class="p-1.5 text-slate-400 hover:text-white rounded-lg transition cursor-pointer"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <div class="p-6 space-y-5">
        <div
          v-if="quotationStore.modalError"
          class="p-3.5 bg-rose-50 rounded-xl border border-rose-200 flex items-start gap-2.5 text-xs text-rose-800"
        >
          <AlertCircle class="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{{ quotationStore.modalError }}</span>
        </div>

        <div v-if="validationErrors.length > 0" class="p-4 bg-rose-50 rounded-xl border border-rose-200">
          <div class="flex items-center gap-2 text-rose-800 font-bold text-xs mb-2">
            <AlertCircle class="w-4 h-4 text-rose-600" />
            <span>Cannot record approval until following requirements are satisfied:</span>
          </div>
          <ul class="list-disc pl-5 text-xs text-rose-700 space-y-1">
            <li v-for="(err, i) in validationErrors" :key="i">{{ err }}</li>
          </ul>
        </div>

        <div v-else class="p-4 bg-green-50 rounded-xl border border-green-200 flex items-start gap-3">
          <CheckCircle2 class="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
          <div>
            <div class="text-xs font-bold text-green-900">Quotation Ready for Approval</div>
            <p class="text-[11px] text-green-800 mt-0.5">
              All {{ quotationStore.totalMaterialsCount }} materials, {{ quotationStore.totalLoadingPointsCount }} loading points, and {{ quotationStore.totalRateGroupsCount }} rate schedules are verified.
            </p>
          </div>
        </div>

        <div class="bg-muted/30 p-4 rounded-xl border border-border space-y-2 text-xs">
          <div class="flex justify-between">
            <span class="text-muted-foreground">Quotation ID:</span>
            <span class="font-mono font-bold text-foreground">{{ quotationStore.quotation.quotationNumber }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Customer:</span>
            <span class="font-semibold text-foreground">{{ quotationStore.quotation.customerName }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Rate Groups:</span>
            <span class="font-semibold text-foreground">{{ quotationStore.totalRateGroupsCount }} groups</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Validity:</span>
            <span class="text-foreground">{{ quotationStore.quotation.validUntil }}</span>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5 flex items-center gap-1.5">
            <Calendar class="w-3.5 h-3.5 text-primary" />
            Customer Approval Date
            <span class="text-destructive ml-1">*</span>
          </label>
          <input
            type="date"
            v-model="approvalDate"
            :min="quotationStore.quotation.quotationDate"
            :max="maxApprovalDate"
            class="w-full border border-input bg-background text-foreground text-sm rounded-lg px-3 py-2 outline-none focus:border-ring"
          />
          <p class="text-[10px] text-muted-foreground mt-1">Must be between Quotation Date and Valid Until, and not in the future.</p>
        </div>

        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Approver Notes (Internal)
          </label>
          <textarea
            v-model="approverNote"
            rows="3"
            placeholder="Add comments for the commercial record..."
            class="w-full border border-input bg-background text-foreground text-xs rounded-lg p-2.5 placeholder:text-muted-foreground outline-none focus:border-ring"
          ></textarea>
        </div>
      </div>

      <div class="px-6 py-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
        <button
          @click="handleCancel"
          :disabled="quotationStore.isSubmitting"
          class="px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted rounded-lg transition cursor-pointer"
        >
          Cancel
        </button>
        <button
          @click="handleSubmit"
          :disabled="!canSubmit || quotationStore.isSubmitting"
          class="inline-flex items-center gap-1.5 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-muted disabled:cursor-not-allowed text-white text-xs font-semibold rounded-lg shadow-xs transition cursor-pointer"
        >
          <Send class="w-3.5 h-3.5" />
          <span>{{ quotationStore.isSubmitting ? 'Recording Approval...' : 'Record Customer Approval' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
