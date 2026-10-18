export type QuotationTabKey = 'all' | 'draft' | 'approved' | 'cancelled'
export type QuotationStatus = Exclude<QuotationTabKey, 'all'>

export interface QuotationMaterial { name?: string; material: string }
export interface QuotationLocation { name?: string; material: string; location_role: 'Loading' | 'Destination'; location: string }
export interface QuotationRate { name?: string; material: string; loading_location: string; unloading_location: string; rate: number | string; effective_from: string; effective_to: string; rate_group?: string }
export interface TransportQuotationDoc {
  name?: string; doctype?: string; docstatus?: number; quotation_date: string; customer: string; valid_until: string; currency: string; status: 'Draft' | 'Approved' | 'Cancelled'
  customer_reference?: string; service_period_from?: string; service_period_to?: string; revision_of?: string; revision_reason?: string
  materials: QuotationMaterial[]; locations: QuotationLocation[]; rates: QuotationRate[]; estimated_quantity?: number | string; estimated_trips?: number | string
  customer_approval_date?: string; customer_approval_reference?: string; customer_approval_notes?: string; customer_approval_attachment?: string; remarks?: string; modified?: string; owner?: string
}

export interface TransportQuotation {
  id: string
  customer: string
  quotationDate: string
  validUntil: string
  materials: string
  rateLines: number
  status: QuotationStatus
  createdBy: string
  modified?: string
  locationCount?: string
}
