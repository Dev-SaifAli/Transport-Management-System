import { apiMock } from '@/config'
import { frappe } from '@/services/frappe/frappeClient'
import type {
  CreateTripRequest,
  CreateTripResponse,
  FleetResourceOptions,
  RouteOptionsResponse,
  TransportJobOption,
} from '@/types/trips'

export interface TripsService {
  getJobs(): Promise<TransportJobOption[]>
  getJobDefaults(jobName: string): Promise<Record<string, unknown>>
  getRouteOptions(jobName: string, loadingSite?: string): Promise<RouteOptionsResponse>
  getFleetResources(material?: string): Promise<FleetResourceOptions>
  createTrip(payload: CreateTripRequest): Promise<CreateTripResponse>
}

function unwrap<T>(response: T | { data: T }): T {
  return (response as { data?: T }).data ?? (response as T)
}

function unwrapMessage<T>(response: unknown): T {
  const payload = unwrap(response as T | { data: T }) as T | { message?: T }
  return (payload as { message?: T }).message ?? (payload as T)
}

const TRIP_MODULE = 'transport_management.transport_management.doctype.transport_trip.transport_trip'

const mockJobs: TransportJobOption[] = [
  {
    name: 'JOB-2026-0001',
    customer: 'Emirates Cement Factory',
    material: 'OPC Cement',
    quantity_mode: 'Open',
    status: 'Ready',
    loading_site: 'RAK Plant',
    unloading_site: 'Jebel Ali',
    requested_date: new Date().toISOString().slice(0, 10),
  },
  {
    name: 'JOB-2026-0002',
    customer: 'Gulf Aggregates Co',
    material: 'Agg 20mm',
    quantity_mode: 'Open',
    status: 'Ready',
    loading_site: 'Fujairah Quarry',
    unloading_site: 'Dubai South',
    requested_date: new Date().toISOString().slice(0, 10),
  },
  {
    name: 'JOB-2026-0003',
    customer: 'Sharjah Precast LLC',
    material: 'Limestone',
    quantity_mode: 'Fixed',
    status: 'Ready',
    loading_site: 'RAK Quarry',
    unloading_site: 'Sajaa',
    requested_date: new Date().toISOString().slice(0, 10),
  },
]

const mockFleet: FleetResourceOptions = {
  trucks: [
    { name: 'DXB-TRK-101', capacity: 35, status: 'Idle' },
    { name: 'DXB-TRK-102', capacity: 35, status: 'Idle' },
    { name: 'SHJ-TRK-201', capacity: 30, status: 'Idle' },
  ],
  drivers: [
    { name: 'DRV-001', full_name: 'Ahmed Khan', status: 'Active' },
    { name: 'DRV-002', full_name: 'Rashid Ali', status: 'Active' },
    { name: 'DRV-003', full_name: 'Bilal Hussain', status: 'Active' },
  ],
  transporters: [
    { name: 'SUP-TRANS-01', supplier_name: 'Al Etihad Logistics' },
    { name: 'SUP-TRANS-02', supplier_name: 'Emirates Haulage LLC' },
  ],
  hiredVehicles: [
    { name: 'HV-901', transporter: 'SUP-TRANS-01' },
    { name: 'HV-902', transporter: 'SUP-TRANS-02' },
  ],
}

const mockService: TripsService = {
  async getJobs(): Promise<TransportJobOption[]> {
    return structuredClone(mockJobs)
  },
  async getJobDefaults(jobName: string): Promise<Record<string, unknown>> {
    const job = mockJobs.find((j) => j.name === jobName) || mockJobs[0]
    return {
      transport_job: job.name,
      material: job.material,
      quantity_mode: job.quantity_mode,
      loading_site: job.loading_site,
      unloading_site: job.unloading_site,
      permitted_loading_points: [job.loading_site, 'Hamriyah Port'].filter(Boolean),
      permitted_destinations: [job.unloading_site, 'Sharjah Industrial'].filter(Boolean),
      permitted_routes: [
        { loading_location: job.loading_site, unloading_location: job.unloading_site },
        { loading_location: 'Hamriyah Port', unloading_location: 'Sharjah Industrial' },
      ],
    }
  },
  async getRouteOptions(jobName: string, loadingSite?: string): Promise<RouteOptionsResponse> {
    const job = mockJobs.find((j) => j.name === jobName) || mockJobs[0]
    const allRoutes = [
      { loading_location: job.loading_site || 'RAK Plant', unloading_location: job.unloading_site || 'Jebel Ali' },
      { loading_location: 'Hamriyah Port', unloading_location: 'Sharjah Industrial' },
    ]
    const filteredRoutes = loadingSite
      ? allRoutes.filter((r) => r.loading_location === loadingSite)
      : allRoutes
    return {
      quantity_mode: job.quantity_mode,
      material: job.material,
      loading_points: [...new Set(allRoutes.map((r) => r.loading_location))],
      destinations: [...new Set(filteredRoutes.map((r) => r.unloading_location))],
      routes: filteredRoutes,
    }
  },
  async getFleetResources(): Promise<FleetResourceOptions> {
    return structuredClone(mockFleet)
  },
  async createTrip(payload: CreateTripRequest): Promise<CreateTripResponse> {
    return {
      name: `TRP-${Date.now().toString().slice(-4)}`,
      status: 'ASSIGNED',
      transport_job: payload.transport_job,
      driver: payload.driver,
      vehicle: payload.vehicle,
      hired_vehicle: payload.hired_vehicle,
    }
  },
}

const frappeService: TripsService = {
  async getJobs(): Promise<TransportJobOption[]> {
    const raw = await frappe.list<TransportJobOption[]>('Transport Job', {
      fields: JSON.stringify([
        'name',
        'customer',
        'material',
        'quantity_mode',
        'status',
        'loading_site',
        'unloading_site',
        'requested_date',
        'sales_order',
      ]),
      filters: JSON.stringify([['status', 'in', ['Draft', 'Pending', 'Ready', 'In Progress']]]),
      order_by: 'creation desc',
      limit_page_length: 200,
    })
    return unwrap(raw) ?? []
  },

  async getJobDefaults(jobName: string): Promise<Record<string, unknown>> {
    const raw = await frappe.call<Record<string, unknown>>(`${TRIP_MODULE}.get_defaults_from_transport_job`, {
      transport_job: jobName,
    })
    return unwrapMessage(raw) ?? {}
  },

  async getRouteOptions(jobName: string, loadingSite?: string): Promise<RouteOptionsResponse> {
    const raw = await frappe.call<RouteOptionsResponse>(`${TRIP_MODULE}.get_trip_route_options`, {
      transport_job: jobName,
      loading_site: loadingSite || null,
    })
    return unwrapMessage(raw)
  },

  async getFleetResources(material?: string): Promise<FleetResourceOptions> {
    const [trucksRes, driversRes, transportersRes, hiredVehiclesRes] = await Promise.all([
      frappe.list<{ name: string; capacity?: number; status?: string }[]>('Truck', {
        fields: JSON.stringify(['name', 'capacity', 'status']),
        filters: JSON.stringify([['disabled', '=', 0]]),
        limit_page_length: 500,
      }),
      frappe.list<{ name: string; full_name?: string; status?: string }[]>('Truck Driver', {
        fields: JSON.stringify(['name', 'full_name', 'status']),
        filters: JSON.stringify([['status', '=', 'Active']]),
        limit_page_length: 500,
      }),
      frappe.list<{ name: string; supplier_name?: string }[]>('Supplier', {
        fields: JSON.stringify(['name', 'supplier_name']),
        filters: JSON.stringify([['is_transporter', '=', 1], ['transporter_status', '=', 'Active'], ['disabled', '=', 0]]),
        limit_page_length: 500,
      }),
      frappe.list<{ name: string; transporter: string }[]>('Hired Vehicle', {
        fields: JSON.stringify(['name', 'transporter']),
        filters: JSON.stringify([['active', '=', 1]]),
        limit_page_length: 500,
      }),
    ])

    return {
      trucks: unwrap(trucksRes) ?? [],
      drivers: unwrap(driversRes) ?? [],
      transporters: unwrap(transportersRes) ?? [],
      hiredVehicles: unwrap(hiredVehiclesRes) ?? [],
    }
  },

  async createTrip(payload: CreateTripRequest): Promise<CreateTripResponse> {
    const raw = await frappe.call<CreateTripResponse>(`${TRIP_MODULE}.create_assigned_transport_trip`, {
      ...payload,
    })
    return unwrapMessage(raw)
  },
}

export function createTripsService(): TripsService {
  return apiMock ? mockService : frappeService
}

