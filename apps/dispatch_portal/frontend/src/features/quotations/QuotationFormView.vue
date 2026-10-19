<script setup lang="ts">
import { ArrowLeft, Save, Plus, Box, AlertTriangle, Send as SendIcon } from 'lucide-vue-next'
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useQuotationFormStore } from './stores/quotationForm'
import QuotationInfoCard from './components/QuotationInfoCard.vue'
import MaterialCard from './components/MaterialCard.vue'
import RateScheduleCard from './components/RateScheduleCard.vue'
import EstimatedRequirementCard from './components/EstimatedRequirementCard.vue'
import QuotationPreviewModal from './components/QuotationPreviewModal.vue'
import SubmitApprovalModal from './components/SubmitApprovalModal.vue'
import SendToCustomerModal from './components/SendToCustomerModal.vue'
import RejectQuotationModal from './components/RejectQuotationModal.vue'
import AddMaterialModal from './components/AddMaterialModal.vue'

const route = useRoute()
const router = useRouter()
const quotationStore = useQuotationFormStore()

const editing = computed(() => typeof route.params.id === 'string' && route.params.id !== 'new')
const canModifyQuotation = computed(
  () =>
    (!editing.value && !quotationStore.isPersisted) ||
    quotationStore.quotation.status === 'Draft' ||
    quotationStore.quotation.status === 'Pending Approval'
)

const pageTitle = computed(() =>
  editing.value
    ? `Edit ${route.params.id}`
    : quotationStore.isPersisted
      ? `Edit ${quotationStore.quotation.quotationNumber}`
      : 'New Transport Quotation'
)

function openSendToCustomerModal() {
  quotationStore.clearModalError()
  quotationStore.sendToCustomerModalOpen = true
}

function openSubmitModal() {
  quotationStore.clearModalError()
  quotationStore.submitModalOpen = true
}

function openRejectModal() {
  quotationStore.clearModalError()
  quotationStore.rejectModalOpen = true
}

function openAddMaterialModal() {
  quotationStore.addMaterialModalOpen = true
}

async function load() {
  await quotationStore.loadMasters()
  if (editing.value) {
    await quotationStore.loadExisting(route.params.id as string)
  } else {
    quotationStore.loadPreset('empty')
  }
}

function handleCancel() {
  if (confirm('Are you sure you want to discard changes to this quotation?')) {
    if (editing.value || quotationStore.isPersisted) {
      router.push('/quotations')
    } else {
      quotationStore.loadPreset('empty')
    }
  }
}

watch(
  () => route.params.id,
  (newId, oldId) => {
    if (newId !== oldId) {
      void load()
    }
  }
)

onMounted(() => {
  void load()
})
</script>

<template>
  <PageContainer class="pb-28">
    <PageHeader :title="pageTitle" subtitle="Customer rates, service period and approval record.">
      <template #actions>
        <Button variant="outline" @click="router.push('/quotations')">
          <ArrowLeft /> Back
        </Button>
        <Badge variant="muted">{{ quotationStore.quotation.status }}</Badge>
        <Button v-if="canModifyQuotation" :disabled="quotationStore.isSaving" @click="quotationStore.saveDraft">
          <Save /> {{ quotationStore.isSaving ? 'Saving...' : 'Save Draft' }}
        </Button>
        <Button v-if="canModifyQuotation" variant="secondary" :disabled="quotationStore.isSendingToCustomer" @click="openSendToCustomerModal">
          <SendIcon /> Send to Customer
        </Button>
        <Button v-if="canModifyQuotation" :disabled="quotationStore.isSubmitting" @click="openSubmitModal">
          Customer Approved
        </Button>
        <Button v-if="canModifyQuotation" variant="destructive" :disabled="quotationStore.isRejecting" @click="openRejectModal">
          <AlertTriangle /> Customer Rejected
        </Button>
      </template>
    </PageHeader>

    <main class="space-y-6">
      <QuotationInfoCard />

      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center gap-2">
              <h2 class="text-base font-bold text-foreground">
                Transportation Materials
              </h2>
              <span class="w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center font-mono">
                {{ quotationStore.totalMaterialsCount }}
              </span>
            </div>
            <p class="text-xs text-muted-foreground mt-0.5">
              {{ quotationStore.totalMaterialsCount === 0 ? 'Each material carries its own loading points, destinations and rates' : 'One quotation · multiple materials · multiple loading areas' }}
            </p>
          </div>

          <button
            @click="openAddMaterialModal"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-card hover:bg-muted border border-border text-foreground text-xs font-semibold rounded-lg shadow-2xs transition cursor-pointer"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>Add Material</span>
          </button>
        </div>

        <div
          v-if="quotationStore.quotation.materials.length === 0"
          class="border-2 border-dashed border-border rounded-2xl p-10 text-center bg-muted/30 space-y-3"
        >
          <div class="w-12 h-12 rounded-xl bg-muted text-muted-foreground flex items-center justify-center mx-auto">
            <Box class="w-6 h-6" />
          </div>
          <h3 class="text-sm font-bold text-foreground">
            No materials added yet
          </h3>
          <p class="text-xs text-muted-foreground max-w-sm mx-auto">
            Add a material to define its loading points, delivery destinations and commercial rates.
          </p>
          <button
            @click="openAddMaterialModal"
            class="inline-flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold rounded-lg shadow-sm transition cursor-pointer"
          >
            <Plus class="w-4 h-4" />
            <span>Add Material</span>
          </button>
        </div>

        <div v-else class="space-y-4">
          <MaterialCard
            v-for="(material, idx) in quotationStore.quotation.materials"
            :key="material.id"
            :material="material"
            :index="idx"
          />

          <button
            @click="openAddMaterialModal"
            class="w-full py-3.5 border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 rounded-xl text-xs font-bold text-primary flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <Plus class="w-4 h-4" />
            <span>Add Material</span>
          </button>
        </div>
      </div>

      <RateScheduleCard />

      <EstimatedRequirementCard />
    </main>

    <footer class="fixed bottom-0 left-0 right-0 z-30 bg-card/95 backdrop-blur border-t border-border shadow-lg">
      <div class="px-4 sm:px-6 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 max-w-screen-2xl mx-auto">
        <div class="text-xs font-medium text-muted-foreground flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-primary"></span>
          <span>{{ quotationStore.summaryBarText }}</span>
        </div>

        <div class="flex items-center gap-2.5 self-end sm:self-auto">
          <Button
            v-if="canModifyQuotation"
            variant="secondary"
            :disabled="quotationStore.isSendingToCustomer"
            @click="openSendToCustomerModal"
          >
            <SendIcon /> Send to Customer
          </Button>
          <Button
            v-if="canModifyQuotation"
            :disabled="quotationStore.isSubmitting"
            @click="openSubmitModal"
          >
            Customer Approved
          </Button>
          <Button
            v-if="canModifyQuotation"
            variant="destructive"
            :disabled="quotationStore.isRejecting"
            @click="openRejectModal"
          >
            <AlertTriangle /> Customer Rejected
          </Button>
          <Button
            v-if="canModifyQuotation"
            :disabled="quotationStore.isSaving"
            @click="quotationStore.saveDraft"
          >
            {{ quotationStore.isSaving ? 'Saving...' : 'Save Draft' }}
          </Button>
          <Button variant="ghost" @click="handleCancel">
            Cancel
          </Button>
        </div>
      </div>
    </footer>
  </PageContainer>

  <AddMaterialModal
    :open="quotationStore.addMaterialModalOpen"
    @close="quotationStore.addMaterialModalOpen = false"
  />
  <QuotationPreviewModal />
  <SubmitApprovalModal />
  <SendToCustomerModal />
  <RejectQuotationModal />
</template>