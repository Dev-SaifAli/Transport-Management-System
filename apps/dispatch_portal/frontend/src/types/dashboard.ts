/** Shared domain types for the Dispatch Portal dashboard. */

export type TripStatus =
  | 'in-transit'
  | 'loading'
  | 'scheduled'
  | 'delivered'
  | 'completed'
  | 'pending'
  | 'correction'
  | 'attention'

export interface KpiStat {
  id: string
  label: string
  value: string
  note: string
  /** Tailwind text color class for the note line. */
  noteClass: string
  icon: string
}

export interface DispatchTrip {
  id: string
  customer: string
  material: string
  origin: string
  destination: string
  truck: string
  driver: string
  /** e.g. "ETA 13:45", "since 12:05", "13:30" */
  timeLabel: string
  status: TripStatus
}

export interface PendingAssignment {
  id: string
  material: string
  origin: string
  destination: string
  /** e.g. "Today 14:00", "Tomorrow 07:00" */
  scheduleLabel: string
}

export interface VerificationItem {
  id: string
  description: string
  /** e.g. "11:42 · Omar F.", "Yesterday · Yasir A." */
  meta: string
  status: 'pending' | 'correction'
}

export type ActivityIcon = 'folder' | 'package' | 'check' | 'shield' | 'truck' | 'user-check'

export interface ActivityItem {
  ref: string
  time: string
  description: string
  icon: ActivityIcon
  /** Tailwind classes for the icon container, e.g. "bg-orange-100 text-orange-600". */
  iconClass: string
}

export interface FleetMapMarker {
  id: string
  status: TripStatus
  /** Marker position as percentages of the map container. */
  x: number
  y: number
  lat?: number
  lng?: number
  label?: string
  tripId?: string
  truck?: string
}

export interface DashboardOverview {
  generatedAt: string
  kpis: KpiStat[]
  todaysDispatch: DispatchTrip[]
  pendingAssignments: PendingAssignment[]
  awaitingVerification: VerificationItem[]
  recentActivity: ActivityItem[]
  fleetMap: {
    markers: FleetMapMarker[]
  }
}
