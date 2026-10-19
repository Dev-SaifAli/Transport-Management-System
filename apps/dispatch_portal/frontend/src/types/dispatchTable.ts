/** Dispatch Table domain types. */

export type TableTripStatus =
  | 'in-transit'
  | 'loading'
  | 'scheduled'
  | 'unassigned'
  | 'delivered'
  | 'completed'

export interface DispatchTableTrip {
  id: string
  status: TableTripStatus
  customer: string
  /** e.g. "RAK Plant · Khor Khwair → Jebel Ali ×2" */
  route: string
  truck: string | null
  driver: string | null
  material: string
  qty: string
  /** e.g. "Today 06:00" */
  window: string
  /** e.g. "AED 95" or null when rate is pending */
  rate: string | null
}

export interface DispatchTableData {
  trips: DispatchTableTrip[]
  /** Pre-applied filters shown as removable pills. */
  activeFilters: { label: string }[]
  meta: {
    totalToday: number
    inTransit: number
    ratePending: number
  }
}