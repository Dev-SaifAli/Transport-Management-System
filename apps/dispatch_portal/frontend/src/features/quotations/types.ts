export interface Customer {
  id: string
  name: string
  customerGroup: string
  territory: string
  contactPerson?: string
  email?: string
  phone?: string
  taxId?: string
}

export interface CargoMaterial {
  id: string
  name: string
  code: string
  cargoType: string
  uom: string
  defaultRate?: number
}

export interface LoadingPoint {
  id: string
  name: string
  area: string
  address?: string
}

export interface DeliveryDestination {
  id: string
  name: string
  emirate: string
  zone?: string
}

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

export interface QuotationMaterial {
  id: string
  materialId: string
  materialName: string
  cargoType: string
  selectedLoadingAreaFilter: string
  selectedLoadingPointIds: string[]
  selectedDestinationIds: string[]
  quickRate?: {
    rate: number
    effectiveFrom: string
    effectiveTo: string
  }
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

export interface Quotation {
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
  materials: QuotationMaterial[]
  estimatedRequirement: EstimatedRequirement
}

export interface SelectOption {
  value: string
  text: string
  subtext?: string
}

export interface MasterOptions {
  customers: SelectOption[]
  materials: CargoMaterial[]
  locations: LoadingPoint[]
  destinations: DeliveryDestination[]
}