export interface TransportJobOption {
  name: string
  customer?: string
  material: string
  quantity_mode: 'Open' | 'Fixed'
  status: string
  loading_site?: string
  unloading_site?: string
  requested_date?: string
  sales_order?: string
}

export interface PermittedRoute {
  loading_location: string
  unloading_location: string
}

export interface RouteOptionsResponse {
  quantity_mode: 'Open' | 'Fixed'
  material: string
  loading_points: string[]
  destinations: string[]
  routes: PermittedRoute[]
}

export interface FleetResourceOptions {
  trucks: { name: string; capacity?: number; status?: string }[]
  drivers: { name: string; full_name?: string; status?: string }[]
  transporters: { name: string; supplier_name?: string }[]
  hiredVehicles: { name: string; transporter: string }[]
}

export interface CreateTripRequest {
  transport_job: string
  trip_date: string
  execution_source: 'OWN' | 'HIRED'
  material: string
  loading_site: string
  unloading_site: string
  planned_quantity?: number
  vehicle?: string
  driver?: string
  transporter?: string
  hired_vehicle?: string
  hired_driver?: string
}

export interface CreateTripResponse {
  name: string
  status: string
  transport_job: string
  driver?: string
  vehicle?: string
  hired_vehicle?: string
}

