import type { DashboardOverview } from '@/types/dashboard'

/**
 * Mock dashboard dataset.
 *
 * Mirrors the structure the Frappe-backed service will eventually return,
 * so swapping the data source does not require any component changes.
 * Values are illustrative operational sample data for AL RANA TRANSPORT LLC.
 */
export const mockDashboardOverview: DashboardOverview = {
  generatedAt: '2025-05-12T12:45:00+04:00',
  kpis: [
    { id: 'todays-trips', label: "Today's Trips", value: '32', note: '+6 vs yesterday', noteClass: 'text-emerald-600', icon: 'users' },
    { id: 'unassigned-trips', label: 'Unassigned Trips', value: '5', note: 'Assign before 14:00', noteClass: 'text-amber-600', icon: 'alert-circle' },
    { id: 'scheduled', label: 'Scheduled', value: '9', note: 'Next at 13:30', noteClass: 'text-blue-700', icon: 'calendar-check' },
    { id: 'active-now', label: 'Active Now', value: '11', note: 'Across 6 jobs', noteClass: 'text-lime-700', icon: 'truck' },
    { id: 'completed', label: 'Completed', value: '7', note: '2 awaiting closure', noteClass: 'text-emerald-600', icon: 'check-circle' },
    { id: 'need-attention', label: 'Need Attention', value: '3', note: '1 delayed · 2 docs', noteClass: 'text-red-600', icon: 'alert-triangle' },
    { id: 'trucks-available', label: 'Trucks Available', value: '14', note: 'of 22 fleet', noteClass: 'text-emerald-600', icon: 'truck' },
    { id: 'drivers-available', label: 'Drivers Available', value: '12', note: 'of 20 roster', noteClass: 'text-emerald-600', icon: 'id-card' },
  ],
  todaysDispatch: [
    {
      id: 'TRP-0142',
      customer: 'Emirates Cement',
      material: 'OPC Cement',
      origin: 'RAK Plant',
      destination: 'Jebel Ali',
      truck: 'DXB T-31455',
      driver: 'Ahmed K.',
      timeLabel: 'ETA 13:45',
      status: 'in-transit',
    },
    {
      id: 'TRP-0143',
      customer: 'Gulf Aggregates',
      material: 'Agg 20mm',
      origin: 'Fujairah Quarry',
      destination: 'Dubai South',
      truck: 'SHJ T-77420',
      driver: 'Bilal H.',
      timeLabel: 'since 12:05',
      status: 'loading',
    },
    {
      id: 'TRP-0151',
      customer: 'Emirates Cement',
      material: 'OPC Cement',
      origin: 'RAK Plant',
      destination: 'Sharjah',
      truck: 'DXB T-51209',
      driver: 'Kamran J.',
      timeLabel: 'ETA 13:20',
      status: 'in-transit',
    },
    {
      id: 'TRP-0144',
      customer: 'National Ready Mix',
      material: 'Washed Sand',
      origin: 'Hamriyah Port',
      destination: 'Sharjah Plant',
      truck: 'RAK T-21880',
      driver: 'Imran S.',
      timeLabel: '13:30',
      status: 'scheduled',
    },
  ],
  pendingAssignments: [
    {
      id: 'TRP-0145',
      material: 'GGBS',
      origin: 'Mussafah',
      destination: 'Al Quoz',
      scheduleLabel: 'Today 14:00',
    },
    {
      id: 'TRP-0149',
      material: 'Agg 10mm',
      origin: 'Fujairah',
      destination: 'Al Ain Rd',
      scheduleLabel: 'Today 15:30',
    },
    {
      id: 'TRP-0154',
      material: 'GGBS',
      origin: 'Mussafah',
      destination: 'Yas Island',
      scheduleLabel: 'Tomorrow 07:00',
    },
  ],
  awaitingVerification: [
    {
      id: 'TRP-0147',
      description: 'Weighbridge slip uploaded',
      meta: '11:42 · Omar F.',
      status: 'pending',
    },
    {
      id: 'TRP-0148',
      description: 'POD uploaded',
      meta: 'Yesterday · Yasir A.',
      status: 'pending',
    },
    {
      id: 'TRP-0151',
      description: 'Weighbridge slip uploaded',
      meta: '09:58 · Kamran J.',
      status: 'correction',
    },
  ],
  recentActivity: [
    { ref: 'TRP-0156', time: '12:40', description: 'Rizwan T. uploaded weighbridge slip', icon: 'folder', iconClass: 'bg-orange-100 text-orange-600' },
    { ref: 'TRP-0143', time: '12:05', description: 'TRP-0143 started loading at Fujairah Quarry', icon: 'package', iconClass: 'bg-orange-100 text-orange-600' },
    { ref: 'TRP-0147', time: '11:42', description: 'Omar F. uploaded weighbridge slip', icon: 'folder', iconClass: 'bg-orange-100 text-orange-600' },
    { ref: 'TRP-0146', time: '11:20', description: 'TRP-0146 marked delivered at Sajaa Ind.', icon: 'check', iconClass: 'bg-emerald-100 text-emerald-600' },
    { ref: 'JOB-2207', time: '10:48', description: 'Supervisor verified POD for TRP-0148', icon: 'shield', iconClass: 'bg-emerald-100 text-emerald-600' },
    { ref: 'JOB-2201', time: '09:25', description: 'TRP-0142 departed RAK Plant · 30.1t', icon: 'truck', iconClass: 'bg-blue-100 text-blue-600' },
    { ref: 'JOB-2201', time: '08:05', description: 'TRP-0142 assigned to DXB T-31455', icon: 'user-check', iconClass: 'bg-blue-100 text-blue-600' },
  ],
  fleetMap: {
    markers: [
      { id: 'TRP-0142', status: 'in-transit', x: 34, y: 62 },
      { id: 'TRP-0146', status: 'delivered', x: 58, y: 30 },
      { id: 'TRP-0156', status: 'in-transit', x: 47, y: 56 },
      { id: 'TRP-0143', status: 'loading', x: 68, y: 44 },
    ],
  },
}
