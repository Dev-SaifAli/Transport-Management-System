<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuotationFormStore } from '../stores/quotationForm'
import { Send, X, ShieldCheck, AlertCircle } from 'lucide-vue-next'

const quotationStore = useQuotationFormStore()

const isSendModalOpen = computed(() => quotationStore.sendToCustomerModalOpen)

const customerNote = ref('Quotation sent for customer review. Awaiting approval.')

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
  quotationStore.quotation.materials.forEach((m) => {
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

const canSend = computed(() => validationErrors.value.length === 0)

function handleSend() {
  if (!canSend.value || quotationStore.isSendingToCustomer) return
  void quotationStore.sendToCustomer(customerNote.value)
}

function handleCancel() {
  if (quotationStore.isSendingToCustomer) return
  quotationStore.clearModalError()
  quotationStore.sendToCustomerModalOpen = false
}

function closeOnOverlayClick(e: MouseEvent) {
  if ((e.target as HTMLElement) === e.currentTarget) {
    handleCancel()
  }
}
</script>

<template>
  <div
    v-if="isSendModalOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto"
    @click="closeOnOverlayClick"
  >
    <div class="relative bg-card rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-border">
      <div class="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <ShieldCheck class="w-5 h-5 text-blue-400" />
          <h3 class="text-base font-bold">Send Quotation to Customer</h3>
        </div>
        <button
          @click="handleCancel"
          :disabled="quotationStore.isSendingToCustomer"
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
            <span>Cannot send until following requirements are satisfied:</span>
          </div>
          <ul class="list-disc pl-5 text-xs text-rose-700 space-y-1">
            <li v-for="(err, i) in validationErrors" :key="i">{{ err }}</li>
          </ul>
        </div>

        <div v-else class="p-4 bg-blue-50 rounded-xl border border-blue-200 flex items-start gap-3">
          <div class="w-5 h-5 text-blue-600 shrink-0 mt-0.5">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          </div>
          <div>
            <div class="text-xs font-bold text-blue-900">Quotation Ready to Send</div>
            <p class="text-[11px] text-blue-800 mt-0.5">
              All {{ quotationStore.totalMaterialsCount }} materials, {{ quotationStore.totalLoadingPointsCount }} loading points, and {{ quotationStore.totalRateGroupsCount }} rate schedules are verified. Rates are <strong>NOT applicable</strong> for Sales Orders or Billing until Customer Approved is recorded.
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
          <label class="block text-xs font-semibold text-foreground mb-1.5">
            Internal Note to Customer
          </label>
          <textarea
            v-model="customerNote"
            rows="3"
            placeholder="Add internal notes about sending this quotation..."
            class="w-full border border-input bg-background text-foreground text-xs rounded-lg p-2.5 placeholder:text-muted-foreground outline-none focus:border-ring"
          ></textarea>
        </div>
      </div>

      <div class="px-6 py-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
        <button
          @click="handleCancel"
          :disabled="quotationStore.isSendingToCustomer"
          class="px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted rounded-lg transition cursor-pointer"
        >
          Cancel
        </button>
        <button
          @click="handleSend"
          :disabled="!canSend || quotationStore.isSendingToCustomer"
          class="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-muted disabled:cursor-not-allowed text-white text-xs font-semibold rounded-lg shadow-xs transition cursor-pointer"
        >
          <Send class="w-3.5 h-3.5" />
          <span>{{ quotationStore.isSendingToCustomer ? 'Sending...' : 'Send to Customer (On Hold)' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
