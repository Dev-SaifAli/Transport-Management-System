import type { BoardTrip, DispatchBoardData } from '@/types/board'

/**
 * Mock dispatch-board dataset. Mirrors what the Frappe-backed service will
 * return so the data source can be swapped without component changes.
 */
export const mockDispatchBoard: DispatchBoardData = {
  columns: [
    { key: 'unassigned', label: 'Unassigned', dotClass: 'bg-red-500' },
    { key: 'scheduled', label: 'Scheduled', dotClass: 'bg-blue-600' },
    { key: 'loading', label: 'Loading', dotClass: 'bg-amber-600' },
    { key: 'in-transit', label: 'In Transit', dotClass: 'bg-blue-600' },
    { key: 'delivered', label: 'Delivered', dotClass: 'bg-emerald-600' },
    { key: 'awaiting-verification', label: 'Awaiting Verif.', dotClass: 'bg-amber-600' },
    { key: 'completed', label: 'Completed', dotClass: 'bg-emerald-600' },
  ],
  trips: [
    // Unassigned (3)
    { id: 'TRP-0145', customer: 'Al Futtain Constr.', origin: 'Mussafah', destination: 'Al Quoz', detail: 'GGBS · 30 t', column: 'unassigned' },
    { id: 'TRP-0149', customer: 'National Ready Mix', origin: 'Fujairah', destination: 'Al Ain Rd', detail: 'Agg 10mm · 25 t', column: 'unassigned' },
    { id: 'TRP-0154', customer: 'National Ready Mix', origin: 'Mussafah', destination: 'Yas Island', detail: 'GGBS · 28 t', column: 'unassigned' },
    // Scheduled (2)
    { id: 'TRP-0144', customer: 'National Ready Mix', origin: 'Hamriyah', destination: 'Sharjah', detail: 'RAK T-21880 · Imran S.', column: 'scheduled' },
    { id: 'TRP-0150', customer: 'Al Futtain Constr.', origin: 'RAK', destination: 'JAFZA', detail: 'DXB T-90533 · Danish R.', column: 'scheduled' },
    // Loading (2)
    { id: 'TRP-0143', customer: 'Gulf Aggregates', origin: 'Fujairah', destination: 'Dubai South', detail: 'SHJ T-77420 · Bilal H.', column: 'loading' },
    { id: 'TRP-0152', customer: 'Gulf Aggregates', origin: 'Fujairah', destination: 'Expo City', detail: 'DXB T-44170 · Nadeem S.', column: 'loading' },
    // In Transit (3)
    { id: 'TRP-0142', customer: 'Emirates Cement', origin: 'RAK', destination: 'Jebel Ali', detail: 'DXB T-31455 · Ahmed K.', column: 'in-transit' },
    { id: 'TRP-0151', customer: 'Emirates Cement', origin: 'RAK', destination: 'Sharjah', detail: 'DXB T-51209 · Kamran J.', column: 'in-transit' },
    { id: 'TRP-0156', customer: 'Gulf Aggregates', origin: 'Hamriyah', destination: 'JLT', detail: 'DXB T-60021 · Rizwan T.', column: 'in-transit' },
    // Delivered (2)
    { id: 'TRP-0146', customer: 'Sharjah Precast', origin: 'RAK Quarry', destination: 'Sajaa', detail: 'AUH T-33871 · Farid M.', column: 'delivered' },
    { id: 'TRP-0155', customer: 'Emirates Cement', origin: 'RAK', destination: 'Dubai South', detail: 'DXB T-19260 · Sohail M.', column: 'delivered' },
    // Awaiting Verification (2)
    { id: 'TRP-0147', customer: 'Emirates Cement', origin: 'RAK', destination: 'Corniche', detail: 'AUH T-15072 · Omar F.', column: 'awaiting-verification' },
    { id: 'TRP-0148', customer: 'Gulf Aggregates', origin: 'Hamriyah', destination: 'DIP', detail: 'DXB T-60214 · Yasir A.', column: 'awaiting-verification' },
    // Completed (2)
    { id: 'TRP-0140', customer: 'Sharjah Precast', origin: 'RAK', destination: 'Sajaa', detail: 'DXB T-48120 · Adil P.', column: 'completed' },
    { id: 'TRP-0139', customer: 'National Ready Mix', origin: 'Hamriyah', destination: 'Sharjah', detail: 'RAK T-21880 · Imran S.', column: 'completed' },
  ] satisfies BoardTrip[],
  hiddenCounts: { unassigned: 2, 'in-transit': 2 },
}