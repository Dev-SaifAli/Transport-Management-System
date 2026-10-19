import { apiMock } from '@/config'
import { mockDispatchBoard } from '@/mock/dispatchBoard'
import { frappe } from '@/services/frappe/frappeClient'
import type { BoardColumnDef, BoardColumnKey, BoardTrip, DispatchBoardData } from '@/types/board'

/** Feature service contract — components depend only on this interface. */
export interface DispatchBoardService {
  getBoard(): Promise<DispatchBoardData>
}

interface BackendTripRow {
  trip?: string
  name?: string
  customer?: string
  status?: string
  source_status?: string
  loading_site?: string
  unloading_site?: string
  material?: string
  planned_quantity?: number
  uom?: string
  vehicle?: string
  driver?: string
}

interface BackendLiveTripsResponse {
  trips?: BackendTripRow[]
}

const BOARD_COLUMNS: BoardColumnDef[] = [
  { key: 'unassigned', label: 'Unassigned', dotClass: 'bg-red-500' },
  { key: 'scheduled', label: 'Scheduled', dotClass: 'bg-blue-600' },
  { key: 'loading', label: 'Loading', dotClass: 'bg-amber-600' },
  { key: 'in-transit', label: 'In Transit', dotClass: 'bg-blue-600' },
  { key: 'delivered', label: 'Delivered', dotClass: 'bg-emerald-600' },
  { key: 'awaiting-verification', label: 'Awaiting Verif.', dotClass: 'bg-amber-600' },
  { key: 'completed', label: 'Completed', dotClass: 'bg-emerald-600' },
]

function unwrap<T>(response: T | { data: T }): T {
  return (response as { data?: T }).data ?? (response as T)
}

function unwrapMessage<T>(response: unknown): T {
  const payload = unwrap(response as T | { data: T }) as T | { message?: T }
  return (payload as { message?: T }).message ?? (payload as T)
}

function mapStatusToColumn(sourceStatus?: string, vehicle?: string, driver?: string): BoardColumnKey {
  const s = (sourceStatus || '').toUpperCase()
  if (s === 'PLANNED') {
    const hasAssignedResource =
      (vehicle && vehicle !== 'Unassigned') || (driver && driver !== 'Unassigned')
    return hasAssignedResource ? 'scheduled' : 'unassigned'
  }
  if (s === 'ASSIGNED') return 'scheduled'
  if (s === 'LOADED') return 'loading'
  if (s === 'IN_TRANSIT') return 'in-transit'
  if (s === 'DELIVERED') return 'delivered'
  if (s === 'POD_RECEIVED' || s === 'EXCEPTION') return 'awaiting-verification'
  if (s === 'CLOSED') return 'completed'
  return 'unassigned'
}

const mockDispatchBoardService: DispatchBoardService = {
  async getBoard(): Promise<DispatchBoardData> {
    await new Promise((resolve) => setTimeout(resolve, 250))
    return structuredClone(mockDispatchBoard)
  },
}

const frappeDispatchBoardService: DispatchBoardService = {
  async getBoard(): Promise<DispatchBoardData> {
    const raw = await frappe.call<BackendLiveTripsResponse>(
      'dispatch_portal.api.frontend.get_live_trips_view',
      { page_length: 200 },
    )
    const payload = unwrapMessage<BackendLiveTripsResponse>(raw) ?? {}
    const rows = (payload.trips ?? []).filter(
      (r) => (r.source_status || r.status || '').toUpperCase() !== 'CANCELLED',
    )

    const trips: BoardTrip[] = rows.map((row) => {
      const src = row.source_status || row.status || 'PLANNED'
      const column = mapStatusToColumn(src, row.vehicle, row.driver)
      const qtyStr =
        row.planned_quantity && Number(row.planned_quantity) > 0
          ? `${Number(row.planned_quantity)} t`
          : ''
      const matDetail = [row.material, qtyStr].filter(Boolean).join(' · ')
      const resourceDetail = [
        row.vehicle && row.vehicle !== 'Unassigned' ? row.vehicle : '',
        row.driver && row.driver !== 'Unassigned' ? row.driver : '',
      ]
        .filter(Boolean)
        .join(' · ')

      const detail =
        column === 'unassigned'
          ? matDetail || 'Awaiting assignment'
          : resourceDetail || matDetail || 'Assigned'

      return {
        id: row.trip || row.name || '',
        customer: row.customer || '—',
        origin: row.loading_site || '—',
        destination: row.unloading_site || '—',
        detail,
        column,
      }
    })

    const hiddenCounts: Partial<Record<BoardColumnKey, number>> = {}
    for (const col of BOARD_COLUMNS) {
      const count = trips.filter((t) => t.column === col.key).length
      if (count > 3) {
        hiddenCounts[col.key] = count - 3
      }
    }

    return {
      columns: BOARD_COLUMNS,
      trips,
      hiddenCounts,
    }
  },
}

export function createDispatchBoardService(): DispatchBoardService {
  return apiMock ? mockDispatchBoardService : frappeDispatchBoardService
}