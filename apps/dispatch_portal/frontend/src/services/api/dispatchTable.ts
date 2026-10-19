import { apiMock } from '@/config'
import { mockDispatchTable } from '@/mock/dispatchTable'
import { frappe } from '@/services/frappe/frappeClient'
import type { DispatchTableData, DispatchTableTrip, TableTripStatus } from '@/types/dispatchTable'

/** Feature service contract — components depend only on this interface. */
export interface DispatchTableService {
  getTrips(): Promise<DispatchTableData>
}

interface BackendTripSummary {
  trip?: string
  name?: string
  customer?: string
  trip_date?: string
  status?: string
  loading_site?: string
  unloading_site?: string
  route?: string
  material?: string
  planned_quantity?: number
  delivered_quantity?: number
  uom?: string
  vehicle?: string | null
  driver?: string | null
  applied_rate_per_ton?: number
  applied_rate_currency?: string
  commercial_rate_status?: string | null
}

interface BackendGetTripsResponse {
  trips?: BackendTripSummary[]
}

function unwrap<T>(response: T | { data: T }): T {
  return (response as { data?: T }).data ?? (response as T)
}

function unwrapMessage<T>(response: unknown): T {
  const payload = unwrap(response as T | { data: T }) as T | { message?: T }
  return (payload as { message?: T }).message ?? (payload as T)
}

function mapTableStatus(status?: string, vehicle?: string | null, driver?: string | null): TableTripStatus {
  const s = (status || '').toUpperCase()
  if (s === 'IN_TRANSIT') return 'in-transit'
  if (s === 'LOADED') return 'loading'
  if (s === 'ASSIGNED') return 'scheduled'
  if (s === 'PLANNED') {
    const hasResource = Boolean(vehicle || driver)
    return hasResource ? 'scheduled' : 'unassigned'
  }
  if (s === 'DELIVERED' || s === 'POD_RECEIVED') return 'delivered'
  if (s === 'CLOSED') return 'completed'
  return 'unassigned'
}

const mockDispatchTableService: DispatchTableService = {
  async getTrips(): Promise<DispatchTableData> {
    await new Promise((resolve) => setTimeout(resolve, 250))
    return structuredClone(mockDispatchTable)
  },
}

const frappeDispatchTableService: DispatchTableService = {
  async getTrips(): Promise<DispatchTableData> {
    const raw = await frappe.call<BackendGetTripsResponse>(
      'dispatch_portal.api.trips.get_trips',
      { page_length: 200 },
    )
    const payload = unwrapMessage<BackendGetTripsResponse>(raw) ?? {}
    const rows = (payload.trips ?? []).filter(
      (r) => (r.status || '').toUpperCase() !== 'CANCELLED',
    )

    let inTransitCount = 0
    let ratePendingCount = 0

    const trips: DispatchTableTrip[] = rows.map((row) => {
      const status = mapTableStatus(row.status, row.vehicle, row.driver)
      if (status === 'in-transit') inTransitCount += 1

      const rateVal = Number(row.applied_rate_per_ton || 0)
      const currency = row.applied_rate_currency || 'AED'
      let rateStr: string | null = null
      if (rateVal > 0) {
        rateStr = `${currency} ${rateVal}`
      } else if (row.commercial_rate_status === 'NOT_APPLICABLE') {
        rateStr = 'Fixed Order'
      } else {
        ratePendingCount += 1
      }

      const qtyVal = Number(row.delivered_quantity || row.planned_quantity || 0)
      const qtyStr = qtyVal > 0 ? `${qtyVal} t` : 'Open t'
      const routeStr =
        row.loading_site && row.unloading_site
          ? `${row.loading_site} → ${row.unloading_site}`
          : row.route || '—'

      return {
        id: row.trip || row.name || '',
        status,
        customer: row.customer || '—',
        route: routeStr,
        truck: row.vehicle || null,
        driver: row.driver || null,
        material: row.material || '—',
        qty: qtyStr,
        window: row.trip_date || '—',
        rate: rateStr,
      }
    })

    return {
      activeFilters: [{ label: 'Live TMS Trips' }],
      meta: {
        totalToday: trips.length,
        inTransit: inTransitCount,
        ratePending: ratePendingCount,
      },
      trips,
    }
  },
}

export function createDispatchTableService(): DispatchTableService {
  return apiMock ? mockDispatchTableService : frappeDispatchTableService
}