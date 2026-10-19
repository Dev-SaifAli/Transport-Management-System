export type QuotationTabKey = 'all' | 'draft' | 'pending_approval' | 'approved' | 'rejected' | 'cancelled'
export type QuotationStatus = Exclude<QuotationTabKey, 'all'>

export interface QuotationMaterial { name?: string; material: string }
export interface QuotationLocation { name?: string; material: string; location_role: 'Loading' | 'Destination'; location: string }
export interface QuotationRate { name?: string; material: string; loading_location: string; unloading_location: string; rate: number | string; effective_from: string; effective_to: string; rate_group?: string }
export interface TransportQuotationDoc {
  name?: string; doctype?: string; docstatus?: number; quotation_date: string; customer: string; valid_until: string; currency: string; status: 'Draft' | 'Pending Approval' | 'Approved' | 'Rejected' | 'Cancelled'
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

// API service types
export interface SelectOption { value: string; text: string; subtext?: string }
export interface MasterLocation { name: string; usage: string; area_zone?: string; city?: string }
export interface MasterOptions { customers: SelectOption[]; materials: string[]; locations: MasterLocation[] }

// Form-specific types (for the new quotation UI)
export interface CargoMaterial { id: string; name: string; code: string; cargoType: string; uom: string }
export interface LoadingPoint { id: string; name: string; area: string; address?: string }
export interface DeliveryDestination { id: string; name: string; emirate: string; zone?: string }

export interface RateGroup {
  id: string
  name: string
  loadingPointIds: string[]
  destinationId: string
  rate: number
  currency: string
  effectiveFrom: string
  effectiveTo: string
  isShared: boolean
}

export interface QuotationMaterialForm {
  id: string
  materialId: string
  materialName: string
  cargoType: string
  selectedLoadingAreaFilter: string
  selectedLoadingPointIds: string[]
  selectedDestinationIds: string[]
  quickRate?: { rate: number; effectiveFrom: string; effectiveTo: string }
  rateGroups: RateGroup[]
  isExpanded: boolean
}

export interface EstimatedRequirement {
  enabled: boolean
  estimatedVolume: number
  volumeUom: string
  truckType: string
  frequency: string
  estimatedTripsPerDay: number
  notes: string
}

export interface QuotationForm {
  quotationNumber: string
  customerId: string
  customerName: string
  quotationDate: string
  validUntil: string
  company: string
  currency: string
  customerReference: string
  remarks: string
  status: 'Draft' | 'Pending Approval' | 'Approved' | 'Rejected'
  materials: QuotationMaterialForm[]
  estimatedRequirement: EstimatedRequirement
}

export interface LinkedSalesOrder {
  sales_order: string
  status: string
  docstatus: number
}

export interface QuotationAreaRate {
  name?: string
  material: string
  loading_location: string
  unloading_location: string
  effective_from: string
  effective_to: string
  rate: number
  converted_sales_order?: LinkedSalesOrder
}

export interface QuotationAreaSummary {
  area_zone: string
  has_valid_area: boolean
  total_rates: number
  converted_rates: number
  is_fully_converted: boolean
  is_partially_converted: boolean
  materials: string[]
  loading_locations: string[]
  unloading_locations: string[]
  sales_orders: LinkedSalesOrder[]
  rates: QuotationAreaRate[]
}

export interface QuotationSalesOrderSummaryResponse {
  quotation: string
  customer: string
  status: string
  docstatus: number
  total_areas: number
  converted_areas: number
  has_unconverted_areas: boolean
  areas: QuotationAreaSummary[]
}