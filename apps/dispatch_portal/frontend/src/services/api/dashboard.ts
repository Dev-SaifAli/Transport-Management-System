import { apiMock } from '@/config'
import { mockDashboardOverview } from '@/mock/dashboard'
import { frappe } from '@/services/frappe/frappeClient'
import type {
  ActivityIcon,
  ActivityItem,
  DashboardOverview,
  DispatchTrip,
  FleetMapMarker,
  KpiStat,
  PendingAssignment,
  TripStatus,
  VerificationItem,
} from '@/types/dashboard'

export interface DashboardService {
  getOverview(): Promise<DashboardOverview>
}

interface BackendTripRow {
  trip?: string
  name?: string
  transport_job?: string
  customer?: string
  trip_date?: string
  status?: string
  source_status?: string
  loading_site?: string
  unloading_site?: string
  material?: string
  planned_quantity?: number
  uom?: string
  vehicle?: string
  driver?: string
  eta?: string
  updated?: string
  modified?: string
  note?: string
}

interface BackendVerificationRow {
  id: string
  name: string
  trip: string
  type: string
  document_type: string
  filename: string
  age: string
  review: string
  confidence: number
}

interface BackendPipelineRow {
  status: string
  source_status: string
  count: number
}

interface BackendDashboardResponse {
  kpis?: {
    trips_today?: number
    planned?: number
    assigned?: number
    in_transit?: number
    pod_pending?: number
    exception?: number
    available_trucks?: number
    active_drivers?: number
  }
  pipeline?: BackendPipelineRow[]
  trips?: BackendTripRow[]
  attention?: BackendTripRow[]
  verification?: BackendVerificationRow[]
}

function unwrap<T>(response: T | { data: T }): T {
  return (response as { data?: T }).data ?? (response as T)
}

function unwrapMessage<T>(response: unknown): T {
  const payload = unwrap(response as T | { data: T }) as T | { message?: T }
  return (payload as { message?: T }).message ?? (payload as T)
}

function mapSourceStatusToDashboardStatus(sourceStatus?: string): TripStatus {
  const s = (sourceStatus || '').toUpperCase()
  if (s === 'IN_TRANSIT') return 'in-transit'
  if (s === 'LOADED') return 'loading'
  if (s === 'ASSIGNED') return 'scheduled'
  if (s === 'DELIVERED') return 'delivered'
  if (s === 'POD_RECEIVED') return 'pending'
  if (s === 'CLOSED') return 'completed'
  if (s === 'EXCEPTION') return 'attention'
  return 'pending'
}

function formatShortTime(datetimeStr?: string): string {
  if (!datetimeStr) return ''
  const match = String(datetimeStr).match(/(\d{2}:\d{2})/)
  return match ? match[1] : String(datetimeStr).slice(0, 10)
}

const mockDashboardService: DashboardService = {
  async getOverview(): Promise<DashboardOverview> {
    await new Promise((resolve) => setTimeout(resolve, 250))
    return structuredClone(mockDashboardOverview)
  },
}

const frappeDashboardService: DashboardService = {
  async getOverview(): Promise<DashboardOverview> {
    const raw = await frappe.call<BackendDashboardResponse>(
      'dispatch_portal.api.frontend.get_dashboard_view',
    )
    const data = unwrapMessage<BackendDashboardResponse>(raw) ?? {}
    const kpiData = data.kpis ?? {}
    const pipeline = data.pipeline ?? []
    const countBySource = (src: string) =>
      pipeline.find((p) => p.source_status === src)?.count ?? 0

    const plannedCount = kpiData.planned ?? countBySource('PLANNED')
    const assignedCount = kpiData.assigned ?? countBySource('ASSIGNED')
    const loadedCount = countBySource('LOADED')
    const inTransitCount = kpiData.in_transit ?? countBySource('IN_TRANSIT')
    const activeNowCount = loadedCount + inTransitCount
    const completedCount = countBySource('CLOSED')
    const podPendingCount = kpiData.pod_pending ?? (countBySource('DELIVERED') + countBySource('POD_RECEIVED'))
    const exceptionCount = kpiData.exception ?? countBySource('EXCEPTION')
    const needAttentionCount = exceptionCount + podPendingCount
    const totalActiveAndToday =
      (kpiData.trips_today ?? 0) > 0
        ? (kpiData.trips_today ?? 0)
        : plannedCount + assignedCount + activeNowCount + podPendingCount

    const kpis: KpiStat[] = [
      {
        id: 'todays-trips',
        label: "Today's Trips",
        value: String(totalActiveAndToday),
        note: `${kpiData.trips_today ?? 0} scheduled today`,
        noteClass: 'text-emerald-600',
        icon: 'users',
      },
      {
        id: 'unassigned-trips',
        label: 'Unassigned Trips',
        value: String(plannedCount),
        note: plannedCount > 0 ? 'Awaiting truck & driver' : 'All trips assigned',
        noteClass: plannedCount > 0 ? 'text-amber-600' : 'text-emerald-600',
        icon: 'alert-circle',
      },
      {
        id: 'scheduled',
        label: 'Scheduled',
        value: String(assignedCount),
        note: 'Assigned & ready',
        noteClass: 'text-blue-700',
        icon: 'calendar-check',
      },
      {
        id: 'active-now',
        label: 'Active Now',
        value: String(activeNowCount),
        note: `${loadedCount} loading · ${inTransitCount} in transit`,
        noteClass: 'text-lime-700',
        icon: 'truck',
      },
      {
        id: 'completed',
        label: 'Completed',
        value: String(completedCount),
        note: `${podPendingCount} awaiting closure`,
        noteClass: 'text-emerald-600',
        icon: 'check-circle',
      },
      {
        id: 'need-attention',
        label: 'Need Attention',
        value: String(needAttentionCount),
        note: `${exceptionCount} exception · ${podPendingCount} POD`,
        noteClass: needAttentionCount > 0 ? 'text-red-600' : 'text-emerald-600',
        icon: 'alert-triangle',
      },
      {
        id: 'trucks-available',
        label: 'Trucks Available',
        value: String(kpiData.available_trucks ?? 0),
        note: 'Idle own fleet',
        noteClass: 'text-emerald-600',
        icon: 'truck',
      },
      {
        id: 'drivers-available',
        label: 'Drivers Available',
        value: String(kpiData.active_drivers ?? 0),
        note: 'Active roster',
        noteClass: 'text-emerald-600',
        icon: 'id-card',
      },
    ]

    const liveTrips = data.trips ?? []
    const todaysDispatch: DispatchTrip[] = liveTrips.slice(0, 8).map((row) => {
      const id = row.trip || row.name || ''
      const src = row.source_status || row.status || 'PLANNED'
      return {
        id,
        customer: row.customer || '—',
        material: row.material || '—',
        origin: row.loading_site || '—',
        destination: row.unloading_site || '—',
        truck: row.vehicle && row.vehicle !== 'Unassigned' ? row.vehicle : 'Unassigned',
        driver: row.driver && row.driver !== 'Unassigned' ? row.driver : 'Unassigned',
        timeLabel: row.eta && row.eta !== '-' ? row.eta : (row.trip_date || row.updated || 'Scheduled'),
        status: mapSourceStatusToDashboardStatus(src),
      }
    })

    const pendingAssignments: PendingAssignment[] = liveTrips
      .filter(
        (r) =>
          (r.source_status || r.status) === 'PLANNED' ||
          r.vehicle === 'Unassigned' ||
          r.driver === 'Unassigned',
      )
      .slice(0, 6)
      .map((row) => ({
        id: row.trip || row.name || '',
        material: row.material || '—',
        origin: row.loading_site || '—',
        destination: row.unloading_site || '—',
        scheduleLabel: row.trip_date ? `Scheduled ${row.trip_date}` : 'Pending assignment',
      }))

    const verificationDocs = data.verification ?? []
    const attentionRows = data.attention ?? []
    const awaitingVerification: VerificationItem[] =
      verificationDocs.length > 0
        ? verificationDocs.slice(0, 6).map((doc) => ({
            id: doc.trip || doc.id,
            description: `${doc.type || doc.document_type} uploaded`,
            meta: `${doc.age || 'Pending review'} · ${doc.filename}`,
            status: 'pending' as const,
          }))
        : attentionRows.slice(0, 6).map((row) => {
            const isException = (row.source_status || row.status) === 'EXCEPTION'
            return {
              id: row.trip || row.name || '',
              description: row.note || (isException ? 'Exception flagged' : 'Awaiting POD verification'),
              meta: `${row.customer || '—'} · ${row.updated || row.trip_date || ''}`,
              status: isException ? ('correction' as const) : ('pending' as const),
            }
          })

    const combinedForActivity = [...liveTrips, ...attentionRows].slice(0, 7)
    const recentActivity: ActivityItem[] = combinedForActivity.map((row) => {
      const src = (row.source_status || row.status || 'PLANNED').toUpperCase()
      const id = row.trip || row.name || ''
      let icon: ActivityIcon = 'truck'
      let iconClass = 'bg-blue-100 text-blue-600'
      let description = `${id} (${row.material || 'Cargo'}) · ${row.loading_site || ''} → ${row.unloading_site || ''}`

      if (src === 'LOADED') {
        icon = 'package'
        iconClass = 'bg-orange-100 text-orange-600'
        description = `${id} loaded at ${row.loading_site || 'loading site'}`
      } else if (src === 'DELIVERED' || src === 'POD_RECEIVED') {
        icon = 'check'
        iconClass = 'bg-emerald-100 text-emerald-600'
        description = `${id} delivered at ${row.unloading_site || 'destination'}`
      } else if (src === 'ASSIGNED') {
        icon = 'user-check'
        iconClass = 'bg-blue-100 text-blue-600'
        description = `${id} assigned to ${row.vehicle || 'fleet'}`
      } else if (src === 'EXCEPTION') {
        icon = 'folder'
        iconClass = 'bg-orange-100 text-orange-600'
        description = row.note || `${id} flagged for dispatcher review`
      }

      return {
        ref: id,
        time: row.updated || formatShortTime(row.modified) || row.trip_date || '',
        description,
        icon,
        iconClass,
      }
    })

    const markerCoords = [
      { x: 34, y: 62 },
      { x: 58, y: 30 },
      { x: 47, y: 56 },
      { x: 68, y: 44 },
      { x: 25, y: 48 },
      { x: 74, y: 60 },
    ]
    const markers: FleetMapMarker[] = liveTrips.slice(0, 6).map((row, idx) => ({
      id: row.trip || row.name || `TRP-${idx + 1}`,
      status: mapSourceStatusToDashboardStatus(row.source_status || row.status),
      x: markerCoords[idx % markerCoords.length].x,
      y: markerCoords[idx % markerCoords.length].y,
    }))

    return {
      generatedAt: new Date().toISOString(),
      kpis,
      todaysDispatch,
      pendingAssignments,
      awaitingVerification,
      recentActivity,
      fleetMap: { markers },
    }
  },
}

export function createDashboardService(): DashboardService {
  return apiMock ? mockDashboardService : frappeDashboardService
}
