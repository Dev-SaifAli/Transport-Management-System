/** Dispatch Board domain types. */

export type BoardColumnKey =
  | 'unassigned'
  | 'scheduled'
  | 'loading'
  | 'in-transit'
  | 'delivered'
  | 'awaiting-verification'
  | 'completed'

export interface BoardTrip {
  id: string
  customer: string
  origin: string
  destination: string
  /** e.g. "GGBS · 30 t" for unassigned, "DXB T-31455 · Ahmed K." for assigned */
  detail: string
  column: BoardColumnKey
}

export interface BoardColumnDef {
  key: BoardColumnKey
  label: string
  /** Tailwind class for the header status dot, e.g. "bg-red-500". */
  dotClass: string
}

export interface DispatchBoardData {
  columns: BoardColumnDef[]
  trips: BoardTrip[]
  /** Trips hidden behind the "+ N more trips" footer per column. */
  hiddenCounts: Partial<Record<BoardColumnKey, number>>
}