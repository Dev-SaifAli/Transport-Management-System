<script setup lang="ts">
import { useQuotationFormStore } from '../stores/quotationForm'
import { X, Printer, Truck, FileText } from 'lucide-vue-next'

const quotationStore = useQuotationFormStore()

function printQuotation() {
  window.print()
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return dateStr
  }
}
</script>

<template>
  <div
    v-if="quotationStore.previewModalOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto"
  >
    <div class="relative bg-card rounded-2xl shadow-2xl max-w-4xl w-full my-8 overflow-hidden border border-border">
      <!-- Modal Header -->
      <div class="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
        <div class="flex items-center gap-3">
          <FileText class="w-5 h-5 text-primary" />
          <h3 class="text-base font-bold">
            Formal Quotation Preview — {{ quotationStore.quotation.quotationNumber }}
          </h3>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="printQuotation"
            class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition cursor-pointer"
          >
            <Printer class="w-3.5 h-3.5" />
            <span>Print</span>
          </button>
          <button
            @click="quotationStore.previewModalOpen = false"
            class="p-1.5 text-slate-400 hover:text-white rounded-lg transition cursor-pointer"
          >
            <X class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Quotation Printable Document Sheet -->
      <div class="p-8 sm:p-10 space-y-8 bg-card text-foreground print:p-0">
        <!-- Letterhead Header -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b-2 border-slate-900 gap-4">
          <div class="flex items-center gap-3.5">
            <div class="w-12 h-12 bg-primary rounded-xl flex items-center justify-center text-primary-foreground shadow-md">
              <Truck class="w-7 h-7" />
            </div>
            <div>
              <h1 class="text-xl font-extrabold tracking-tight text-foreground">
                AL RANA TRANSPORT LLC
              </h1>
              <p class="text-xs text-muted-foreground uppercase tracking-widest font-semibold">
                Heavy Bulk Haulage & Industrial Fleet Operations
              </p>
              <p class="text-[11px] text-muted-foreground font-mono">
                TRN: 100293847500003 · Dubai, United Arab Emirates
              </p>
            </div>
          </div>

          <div class="sm:text-right">
            <div class="inline-block px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
              Commercial Quotation
            </div>
            <div class="text-lg font-mono font-bold text-foreground mt-1">
              {{ quotationStore.quotation.quotationNumber }}
            </div>
            <div class="text-xs text-muted-foreground">
              Status: <span class="font-semibold text-foreground">{{ quotationStore.quotation.status }}</span>
            </div>
          </div>
        </div>

        <!-- Meta Details Box -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 bg-muted/30 p-5 rounded-xl border border-border text-xs">
          <div>
            <div class="text-[11px] font-bold uppercase text-muted-foreground mb-1">Quotation For</div>
            <div class="text-sm font-bold text-foreground">
              {{ quotationStore.quotation.customerName || 'Customer Not Specified' }}
            </div>
            <div class="text-muted-foreground mt-1">
              Linked ERP Master: <span class="font-mono text-primary font-semibold">{{ quotationStore.quotation.customerId }}</span>
            </div>
            <div v-if="quotationStore.quotation.customerReference" class="text-muted-foreground mt-0.5">
              Ref: {{ quotationStore.quotation.customerReference }}
            </div>
          </div>

          <div class="sm:text-right space-y-1">
            <div>
              <span class="text-muted-foreground">Date Issued: </span>
              <span class="font-semibold text-foreground">{{ formatDate(quotationStore.quotation.quotationDate) }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Validity: </span>
              <span class="font-semibold text-foreground">{{ formatDate(quotationStore.quotation.validUntil) }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Billing Currency: </span>
              <span class="font-semibold text-foreground">{{ quotationStore.quotation.currency }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Issued by: </span>
              <span class="font-semibold text-foreground">Ahmad Raza (Sales & Pricing)</span>
            </div>
          </div>
        </div>

        <!-- Materials & Commercial Rates Table -->
        <div>
          <h4 class="text-xs font-bold uppercase tracking-wider text-foreground mb-3 flex items-center justify-between">
            <span>Approved Transportation Rate Schedule</span>
            <span class="text-[11px] text-muted-foreground font-mono">{{ quotationStore.allRateLines.length }} Rate Line(s)</span>
          </h4>

          <div class="overflow-x-auto rounded-xl border border-border">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="bg-muted text-muted-foreground uppercase tracking-wider text-[11px] border-b border-border">
                  <th class="py-2.5 px-3 font-bold">#</th>
                  <th class="py-2.5 px-3 font-bold">Material Cargo</th>
                  <th class="py-2.5 px-3 font-bold">Origin / Loading Point</th>
                  <th class="py-2.5 px-3 font-bold">Delivery Destination</th>
                  <th class="py-2.5 px-3 font-bold text-right">Agreed Rate</th>
                  <th class="py-2.5 px-3 font-bold">Validity Window</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border">
                <tr
                  v-for="(line, idx) in quotationStore.allRateLines"
                  :key="idx"
                  class="hover:bg-muted/30"
                >
                  <td class="py-2.5 px-3 font-mono text-muted-foreground">{{ idx + 1 }}</td>
                  <td class="py-2.5 px-3 font-bold text-foreground">{{ line.materialName }}</td>
                  <td class="py-2.5 px-3 text-foreground font-medium">{{ line.loadingPointsNames }}</td>
                  <td class="py-2.5 px-3 text-foreground">{{ line.destinationName }}</td>
                  <td class="py-2.5 px-3 font-bold text-foreground text-right font-mono text-sm">
                    {{ line.currency }} {{ Number(line.rate).toFixed(2) }}/TON
                  </td>
                  <td class="py-2.5 px-3 text-muted-foreground font-mono text-[11px]">{{ line.effectiveText }}</td>
                </tr>
                <tr v-if="quotationStore.allRateLines.length === 0">
                  <td colspan="6" class="py-6 text-center text-muted-foreground italic">
                    No commercial rate groups configured yet.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Remarks & Terms -->
        <div class="p-4 bg-muted/30 rounded-xl border border-border text-xs space-y-2">
          <div class="font-bold text-foreground">Operational Terms & Special Conditions:</div>
          <p class="text-muted-foreground leading-relaxed">
            {{ quotationStore.quotation.remarks || 'Standard Al Rana Transport LLC demurrage rules apply after 3 hours free time at loading and offloading sites.' }}
          </p>
          <ul class="list-disc pl-5 text-[11px] text-muted-foreground space-y-0.5">
            <li>Rates are exclusive of 5% UAE VAT, which will be invoiced in accordance with FTA regulations.</li>
            <li>All rates are subject to confirmed road and quarry permits as per local RTA / Ministry rules.</li>
            <li>Weighbridge slip at loading and destination shall serve as certified proof of payload tonnage.</li>
          </ul>
        </div>

        <!-- Signature Authorization Blocks -->
        <div class="pt-6 grid grid-cols-2 gap-8 border-t border-border text-xs">
          <div>
            <p class="text-[11px] font-semibold text-muted-foreground uppercase">Authorized Transport Manager</p>
            <div class="h-14 flex items-end">
              <span class="font-serif italic text-base text-foreground">Ahmad Raza</span>
            </div>
            <div class="border-t border-border pt-1 text-muted-foreground">
              Al Rana Transport LLC · Pricing Desk
            </div>
          </div>
          <div>
            <p class="text-[11px] font-semibold text-muted-foreground uppercase">Customer Acceptance Signature</p>
            <div class="h-14"></div>
            <div class="border-t border-border pt-1 text-muted-foreground">
              Authorized Signatory & Seal
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="px-6 py-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
        <button
          @click="quotationStore.previewModalOpen = false"
          class="px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted rounded-lg transition cursor-pointer"
        >
          Close Preview
        </button>
      </div>
    </div>
  </div>
</template>