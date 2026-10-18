import type { DispatchTableData, DispatchTableTrip } from '@/types/dispatchTable'

/**
 * Mock Dispatch Table dataset — same 16 trips as the board, flattened into
 * grid rows. Mirrors the Frappe-backed response shape.
 */
export const mockDispatchTable: DispatchTableData = {
  activeFilters: [{ label: 'Date: Today' }, { label: 'Fleet: AL RANA' }],
  meta: { totalToday: 16, inTransit: 6, ratePending: 2 },
  trips: [
    { id: 'TRP-0142', status: 'in-transit', customer: 'Emirates Cement Factory', route: 'RAK Plant · Khor Khwair → Jebel Ali ×2', truck: 'DXB T-31455', driver: 'Ahmed K.', material: 'OPC Cement', qty: '24 t', window: 'Today 06:00', rate: 'AED 95' },
    { id: 'TRP-0156', status: 'in-transit', customer: 'Gulf Aggregates Co', route: 'Hamriyah Port · SAIF Zone → JLT ×2', truck: 'DXB T-60021', driver: 'Rizwan T.', material: 'Agg 20mm', qty: '28 t', window: 'Today 06:30', rate: 'AED 110' },
    { id: 'TRP-0151', status: 'in-transit', customer: 'Emirates Cement Factory', route: 'RAK Plant → Sharjah', truck: 'DXB T-51209', driver: 'Kamran J.', material: 'OPC Cement', qty: '24 t', window: 'Today 07:00', rate: 'AED 88' },
    { id: 'TRP-0143', status: 'loading', customer: 'Gulf Aggregates Co', route: 'Fujairah · Tawyeen → Dubai South ×2', truck: 'SHJ T-77420', driver: 'Bilal H.', material: 'Agg 20mm', qty: '25 t', window: 'Today 07:30', rate: 'AED 102' },
    { id: 'TRP-0152', status: 'loading', customer: 'Gulf Aggregates Co', route: 'Fujairah Quarry → Expo City', truck: 'DXB T-44170', driver: 'Nadeem S.', material: 'Agg 10mm', qty: '26 t', window: 'Today 08:00', rate: null },
    { id: 'TRP-0144', status: 'scheduled', customer: 'National Ready Mix', route: 'Hamriyah Port → Sharjah Plant', truck: 'RAK T-21880', driver: 'Imran S.', material: 'Washed Sand', qty: '25 t', window: 'Today 09:00', rate: 'AED 74' },
    { id: 'TRP-0150', status: 'scheduled', customer: 'Al Futtain Construction', route: 'RAK Plant · Ghayathi → JAFZA ×2', truck: 'DXB T-90533', driver: 'Danish R.', material: 'GGBS', qty: '30 t', window: 'Today 10:30', rate: 'AED 120' },
    { id: 'TRP-0145', status: 'unassigned', customer: 'Al Futtain Construction', route: 'Mussafah · ICAD Yard → Al Quoz ×2', truck: null, driver: null, material: 'GGBS', qty: '30 t', window: 'Today 12:00', rate: null },
    { id: 'TRP-0146', status: 'delivered', customer: 'Sharjah Precast', route: 'RAK Quarry → Sajaa', truck: 'AUH T-33871', driver: 'Farid M.', material: 'Limestone', qty: '27 t', window: 'Today 05:30', rate: 'AED 90' },
    { id: 'TRP-0140', status: 'completed', customer: 'Sharjah Precast', route: 'RAK Plant → Sajaa', truck: 'DXB T-48120', driver: 'Adil P.', material: 'Limestone', qty: '27 t', window: 'Today 04:30', rate: 'AED 92' },
    { id: 'TRP-0149', status: 'unassigned', customer: 'National Ready Mix', route: 'Fujairah → Al Ain Rd', truck: null, driver: null, material: 'Agg 10mm', qty: '25 t', window: 'Today 15:30', rate: 'AED 98' },
    { id: 'TRP-0154', status: 'unassigned', customer: 'National Ready Mix', route: 'Mussafah → Yas Island', truck: null, driver: null, material: 'GGBS', qty: '28 t', window: 'Tomorrow 07:00', rate: 'AED 105' },
    { id: 'TRP-0147', status: 'in-transit', customer: 'Emirates Cement Factory', route: 'RAK → Corniche', truck: 'AUH T-15072', driver: 'Omar F.', material: 'OPC Cement', qty: '24 t', window: 'Today 05:00', rate: 'AED 95' },
    { id: 'TRP-0148', status: 'in-transit', customer: 'Gulf Aggregates Co', route: 'Hamriyah → DIP', truck: 'DXB T-60214', driver: 'Yasir A.', material: 'Agg 20mm', qty: '25 t', window: 'Today 05:45', rate: 'AED 102' },
    { id: 'TRP-0153', status: 'in-transit', customer: 'Sharjah Precast', route: 'RAK Quarry → Sajaa', truck: 'DXB T-19260', driver: 'Sohail M.', material: 'Limestone', qty: '27 t', window: 'Today 06:15', rate: 'AED 90' },
    { id: 'TRP-0139', status: 'in-transit', customer: 'National Ready Mix', route: 'Hamriyah → Sharjah', truck: 'RAK T-21880', driver: 'Imran S.', material: 'Washed Sand', qty: '25 t', window: 'Today 04:00', rate: 'AED 74' },
  ] satisfies DispatchTableTrip[],
}