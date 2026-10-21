<script setup lang="ts">
import { onClickOutside, onKeyStroke } from '@vueuse/core'
import { AlertTriangle, ArrowLeft, CheckCircle2, ChevronDown, Plus, Box, Send as SendIcon } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
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

const actionsMenuOpen = ref(false)
const actionsMenuRef = ref<HTMLElement | null>(null)
onClickOutside(actionsMenuRef, () => {
  actionsMenuOpen.value = false
})

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

const statusBadgeVariant = computed(() => {
  const st = quotationStore.displayStatus
  if (st === 'Saved') return 'green'
  if (st === 'Approved') return 'green'
  if (st === 'Pending Approval') return 'amber'
  if (st === 'Rejected') return 'red'
  return 'muted'
})

async function handleSave() {
  const result = await quotationStore.saveDraft()
  if (result && result.name && (!editing.value || route.params.id === 'new')) {
    await router.replace(`/quotations/${result.name}/edit`)
  }
}

onKeyStroke(['s', 'S'], (e) => {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    if (canModifyQuotation.value && !quotationStore.isSaving) {
      void handleSave()
    }
  }
})

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
  <PageContainer class="pb-28 bg-slate-50/80 min-h-screen">
    <PageHeader :title="pageTitle" subtitle="Customer rates, service period and approval record.">
      <template #actions>
        <Button
          variant="outline"
          class="h-9 rounded-lg border-slate-300 bg-white px-4 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 cursor-pointer"
          @click="router.push('/quotations')"
        >
          <ArrowLeft class="size-3.5" aria-hidden="true" />
          Back
        </Button>
        <Badge :variant="statusBadgeVariant" class="px-3 py-1 text-xs font-semibold capitalize transition-colors rounded-lg">
          {{ quotationStore.displayStatus }}
        </Badge>
      </template>
    </PageHeader>

    <main
      class="space-y-6 transition-opacity duration-200"
      :class="{ 'opacity-50 pointer-events-none select-none': quotationStore.isSaving }"
    >
      <QuotationInfoCard />

      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center gap-2">
              <h2 class="text-base font-bold text-slate-900">
                Transportation Materials
              </h2>
              <span class="w-5 h-5 rounded-md bg-blue-50 text-blue-700 text-xs font-bold flex items-center justify-center font-mono border border-blue-200/70">
                {{ quotationStore.totalMaterialsCount }}
              </span>
            </div>
            <p class="text-xs text-slate-500 mt-0.5">
              {{ quotationStore.totalMaterialsCount === 0 ? 'Each material carries its own loading points, destinations and rates' : 'One quotation · multiple materials · multiple loading areas' }}
            </p>
          </div>

          <button
            @click="openAddMaterialModal"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg shadow-2xs transition cursor-pointer"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>Add Material</span>
          </button>
        </div>

        <div
          v-if="quotationStore.quotation.materials.length === 0"
          class="border-2 border-dashed border-slate-200 rounded-xl p-10 text-center bg-white space-y-3 shadow-xs"
        >
          <div class="w-12 h-12 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center mx-auto">
            <Box class="w-6 h-6" />
          </div>
          <h3 class="text-sm font-bold text-slate-900">
            No materials added yet
          </h3>
          <p class="text-xs text-slate-500 max-w-sm mx-auto">
            Add a material to define its loading points, delivery destinations and commercial rates.
          </p>
          <button
            @click="openAddMaterialModal"
            class="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition cursor-pointer"
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
            class="w-full py-3.5 border-2 border-dashed border-slate-300 hover:border-blue-600 hover:bg-blue-50/40 rounded-xl text-xs font-bold text-blue-600 flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <Plus class="w-4 h-4" />
            <span>Add Material</span>
          </button>
        </div>
      </div>

      <RateScheduleCard />

      <EstimatedRequirementCard />
    </main>

    <footer class="fixed bottom-0 left-0 right-0 z-30 border-t border-slate-200 bg-white/95 backdrop-blur-md shadow-lg overflow-visible">
      <div class="mx-auto flex max-w-screen-2xl flex-nowrap items-center justify-between gap-4 px-4 py-3 sm:px-6 whitespace-nowrap overflow-visible">
        <div class="flex shrink-0 items-center gap-2 text-xs font-medium text-slate-500">
          <span class="size-2 rounded-full bg-[#0466C8]" aria-hidden="true" />
          <span>{{ quotationStore.summaryBarText }}</span>
        </div>

        <div class="flex shrink-0 flex-nowrap items-center gap-2.5 whitespace-nowrap">
          <Button
            variant="ghost"
            class="h-9 rounded-lg px-4 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
            @click="handleCancel"
          >
            Cancel
          </Button>

          <!-- State A: New / Unpersisted quotation -->
          <template v-if="!quotationStore.isPersisted">
            <Button
              class="h-9 rounded-lg border-0 bg-[#0466C8] px-6 text-xs font-bold text-white shadow-sm transition-all hover:bg-[#0353A4] focus-visible:ring-2 focus-visible:ring-[#0466C8]/50 cursor-pointer"
              :disabled="quotationStore.isSaving"
              @click="handleSave"
            >
              {{ quotationStore.isSaving ? 'Saving…' : 'Save' }}
            </Button>
          </template>

          <!-- State B: Persisted Draft or Modifiable quotation -->
          <template v-else-if="canModifyQuotation">
            <Button
              variant="outline"
              class="h-9 rounded-lg border-slate-300 bg-white px-4 text-xs font-semibold text-slate-700 shadow-xs transition-all hover:bg-slate-50 cursor-pointer"
              :disabled="quotationStore.isSaving"
              @click="handleSave"
            >
              {{ quotationStore.isSaving ? 'Saving…' : 'Save' }}
            </Button>

            <Button
              v-if="quotationStore.quotation.status === 'Draft'"
              class="h-9 rounded-lg border-0 bg-[#0466C8] px-5 text-xs font-bold text-white shadow-sm transition-all hover:bg-[#0353A4] focus-visible:ring-2 focus-visible:ring-[#0466C8]/50 cursor-pointer"
              :disabled="quotationStore.isSendingToCustomer"
              @click="openSendToCustomerModal"
            >
              <SendIcon class="size-3.5 text-white" aria-hidden="true" />
              Send to Customer
            </Button>

            <!-- Actions Dropdown to prevent wrapping -->
            <div ref="actionsMenuRef" class="relative">
              <Button
                variant="outline"
                class="h-9 rounded-lg border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 shadow-xs transition-all hover:bg-slate-50 cursor-pointer"
                @click="actionsMenuOpen = !actionsMenuOpen"
                aria-haspopup="true"
                :aria-expanded="actionsMenuOpen"
              >
                Actions
                <ChevronDown class="size-3 text-slate-500 transition-transform" :class="{ 'rotate-180': actionsMenuOpen }" />
              </Button>

              <div
                v-if="actionsMenuOpen"
                class="absolute bottom-full right-0 mb-3 z-50 w-52 rounded-lg border border-slate-200 bg-white p-1.5 shadow-xl"
                @click="actionsMenuOpen = false"
              >
                <button
                  type="button"
                  class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 cursor-pointer"
                  :disabled="quotationStore.isSubmitting"
                  @click="openSubmitModal"
                >
                  <CheckCircle2 class="size-3.5 text-emerald-600" />
                  Customer Approved
                </button>
                <button
                  type="button"
                  class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-rose-600 transition-colors hover:bg-rose-50 cursor-pointer"
                  :disabled="quotationStore.isRejecting"
                  @click="openRejectModal"
                >
                  <AlertTriangle class="size-3.5 text-rose-600" />
                  Customer Rejected
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </footer>
  </PageContainer>

  <!-- Saving Lock Overlay -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="quotationStore.isSaving"
        class="fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-xs pointer-events-auto select-none"
      >
        <div class="flex items-center gap-3 rounded-2xl border border-border/80 bg-card px-6 py-4 shadow-xl">
          <span class="size-4 animate-spin rounded-full border-2 border-[#0466C8] border-t-transparent" />
          <p class="text-sm font-semibold text-foreground">Saving quotation…</p>
        </div>
      </div>
    </Transition>
  </Teleport>

  <AddMaterialModal
    :open="quotationStore.addMaterialModalOpen"
    @close="quotationStore.addMaterialModalOpen = false"
  />
  <QuotationPreviewModal />
  <SubmitApprovalModal />
  <SendToCustomerModal />
  <RejectQuotationModal />
</template>