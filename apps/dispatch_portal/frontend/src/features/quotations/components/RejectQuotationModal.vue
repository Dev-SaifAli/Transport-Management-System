<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuotationFormStore } from '../stores/quotationForm'
import { AlertTriangle, AlertCircle, X, Trash2 } from 'lucide-vue-next'

const quotationStore = useQuotationFormStore()

const isRejectModalOpen = computed(() => quotationStore.rejectModalOpen)

const rejectionReason = ref('Customer declined the quotation terms.')

const validationErrors = computed(() => {
  const errors: string[] = []
  if (!quotationStore.quotation.customerId && !quotationStore.quotation.customerName) {
    errors.push('Customer must be selected from ERPNext master')
  }
  if (!rejectionReason.value.trim()) {
    errors.push('Rejection reason is required')
  }
  return errors
})

const canReject = computed(() => validationErrors.value.length === 0)

function handleReject() {
  if (!canReject.value || quotationStore.isRejecting) return
  void quotationStore.rejectQuotation(rejectionReason.value)
}

function handleCancel() {
  if (quotationStore.isRejecting) return
  quotationStore.clearModalError()
  quotationStore.rejectModalOpen = false
}

function closeOnOverlayClick(e: MouseEvent) {
  if ((e.target as HTMLElement) === e.currentTarget) {
    handleCancel()
  }
}
</script>

<template>
  <div
    v-if="isRejectModalOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto"
    @click="closeOnOverlayClick"
  >
    <div class="relative bg-card rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-border">
      <div class="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <AlertTriangle class="w-5 h-5 text-rose-400" />
          <h3 class="text-base font-bold">Mark Quotation as Customer Rejected</h3>
        </div>
        <button
          @click="handleCancel"
          :disabled="quotationStore.isRejecting"
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

        <div class="p-4 bg-rose-50 rounded-xl border border-rose-200 flex items-start gap-3">
          <AlertTriangle class="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <div class="text-xs font-bold text-rose-900">This action will mark the quotation as Rejected</div>
            <p class="text-[11px] text-rose-800 mt-0.5">
              The quotation will be marked as <strong>Rejected</strong> in the system without submitting it. Rejected quotations cannot be used for Sales Orders, Trips, or Billing.
            </p>
          </div>
        </div>

        <div v-if="validationErrors.length > 0" class="p-4 bg-rose-50 rounded-xl border border-rose-200">
          <div class="flex items-center gap-2 text-rose-800 font-bold text-xs mb-2">
            <AlertTriangle class="w-4 h-4 text-rose-600" />
            <span>Requirements not met:</span>
          </div>
          <ul class="list-disc pl-5 text-xs text-rose-700 space-y-1">
            <li v-for="(err, i) in validationErrors" :key="i">{{ err }}</li>
          </ul>
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
            <span class="text-muted-foreground">Status after rejection:</span>
            <span class="font-semibold text-rose-600">Rejected</span>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Rejection Reason (Internal) <span class="text-destructive ml-1">*</span>
          </label>
          <textarea
            v-model="rejectionReason"
            rows="3"
            placeholder="Reason for rejection..."
            class="w-full border border-input bg-background text-foreground text-xs rounded-lg p-2.5 placeholder:text-muted-foreground outline-none focus:border-ring"
          ></textarea>
        </div>
      </div>

      <div class="px-6 py-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
        <button
          @click="handleCancel"
          :disabled="quotationStore.isRejecting"
          class="px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted rounded-lg transition cursor-pointer"
        >
          Cancel
        </button>
        <button
          @click="handleReject"
          :disabled="!canReject || quotationStore.isRejecting"
          class="inline-flex items-center gap-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-700 disabled:bg-muted disabled:cursor-not-allowed text-white text-xs font-semibold rounded-lg shadow-xs transition cursor-pointer"
        >
          <Trash2 class="w-3.5 h-3.5" />
          <span>{{ quotationStore.isRejecting ? 'Rejecting...' : 'Confirm Rejection' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
