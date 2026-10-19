import type { QuotationTabKey, TransportQuotation } from '@/types/quotations'

export const mockQuotations: TransportQuotation[] = [
  { id: 'QTN-2025-0141', customer: 'Gulf Aggregates Co', quotationDate: '08 May 2025', validUntil: '08 Aug 2025', materials: 'Aggregate 20mm · 10mm', rateLines: 3, status: 'approved', createdBy: 'S. Raza' },
  { id: 'QTN-2025-0138', customer: 'Emirates Cement Factory', quotationDate: '05 May 2025', validUntil: '05 Nov 2025', materials: 'OPC Cement · GGBS', rateLines: 4, status: 'approved', createdBy: 'S. Raza' },
  { id: 'QTN-2025-0136', customer: 'National Ready Mix', quotationDate: '02 May 2025', validUntil: '02 Aug 2025', materials: 'Washed Sand', rateLines: 2, status: 'approved', createdBy: 'M. Iqbal' },
  { id: 'QTN-2025-0133', customer: 'Al Futtain Construction', quotationDate: '28 Apr 2025', validUntil: '28 Jul 2025', materials: 'GGBS', rateLines: 2, status: 'approved', createdBy: 'S. Raza' },
  { id: 'QTN-2025-0142', customer: 'Sharjah Precast', quotationDate: '11 May 2025', validUntil: '11 Aug 2025', materials: 'Limestone', rateLines: 1, status: 'draft', createdBy: 'M. Iqbal' },
  { id: 'QTN-2025-0140', customer: 'Gulf Aggregates Co', quotationDate: '09 May 2025', validUntil: '09 Aug 2025', materials: 'Agg 20mm', rateLines: 1, status: 'draft', createdBy: 'S. Raza' },
  { id: 'QTN-2025-0117', customer: 'Sharjah Precast', quotationDate: '10 Jan 2025', validUntil: '10 Apr 2025', materials: 'Limestone', rateLines: 2, status: 'cancelled', createdBy: 'S. Raza' },
  { id: 'QTN-2025-0102', customer: 'Bin Hafeet Transport', quotationDate: '02 Jan 2025', validUntil: '02 Apr 2025', materials: 'Dune Sand', rateLines: 1, status: 'cancelled', createdBy: 'M. Iqbal' },
]

export const mockQuotationTabs: { key: QuotationTabKey; label: string; count: number }[] = [
  { key: 'all', label: 'All', count: 8 },
  { key: 'draft', label: 'Draft', count: 2 },
  { key: 'pending_approval', label: 'Pending Approval', count: 0 },
  { key: 'approved', label: 'Approved', count: 4 },
  { key: 'rejected', label: 'Rejected', count: 0 },
  { key: 'cancelled', label: 'Cancelled', count: 2 },
]
