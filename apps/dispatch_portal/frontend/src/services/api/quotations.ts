import { apiMock } from '@/config'
import { frappe } from '@/services/frappe/frappeClient'
import { mockQuotationTabs, mockQuotations } from '@/mock/quotations'
import type { QuotationSalesOrderSummaryResponse, QuotationTabKey, TransportQuotation, TransportQuotationDoc } from '@/types/quotations'

export interface QuotationsResponse { tabs: { key: QuotationTabKey; label: string; count: number }[]; rows: TransportQuotation[] }
export interface SelectOption { value: string; text: string; subtext?: string }
export interface MasterLocation { name: string; usage: string; area_zone?: string; city?: string }
export interface MasterOptions { customers: SelectOption[]; materials: string[]; locations: MasterLocation[] }
export interface MasterSearchApi { searchCustomers(query: string): Promise<SelectOption[]>; searchMaterials(query: string): Promise<string[]>; searchLocations(query: string, role?: 'Loading' | 'Destination'): Promise<SelectOption[]> }
function unwrap<T>(response: T | { data: T }): T { return (response as { data?: T }).data ?? response as T }
function unwrapMessage<T>(response: unknown): T {
  const payload = unwrap(response as T | { data: T }) as T | { message?: T }
  return (payload as { message?: T }).message ?? payload as T
}
function statusOf(doc: Partial<TransportQuotationDoc>): TransportQuotation['status'] {
  if (doc.status === 'Approved' || doc.docstatus === 1) return 'approved'
  if (doc.status === 'Cancelled' || doc.docstatus === 2) return 'cancelled'
  if (doc.status === 'Rejected') return 'rejected'
  if (doc.status === 'Pending Approval') return 'pending_approval'
  return 'draft'
}
function asRow(doc: TransportQuotationDoc): TransportQuotation {
  const materials = (doc.materials ?? []).map((row) => row.material).filter(Boolean)
  const loading = new Set((doc.locations ?? []).filter((row) => row.location_role === 'Loading').map((row) => row.location)).size
  const destinations = new Set((doc.locations ?? []).filter((row) => row.location_role === 'Destination').map((row) => row.location)).size
  return { id: doc.name ?? '', customer: doc.customer, quotationDate: doc.quotation_date, validUntil: doc.valid_until, materials: materials.length ? materials.join(', ') : '—', rateLines: doc.rates?.length ?? 0, status: statusOf(doc), createdBy: doc.owner ?? '', modified: doc.modified, locationCount: loading || destinations ? `${loading} loading → ${destinations} destination` : '—' }
}
const mockService = { async getQuotations(): Promise<QuotationsResponse> { return structuredClone({ tabs: mockQuotationTabs, rows: mockQuotations }) } }
const QUOTATION_MODULE = 'transport_management.transport_management.doctype.transport_quotation.transport_quotation'
const frappeService = {
  async getQuotations(): Promise<QuotationsResponse> {
    const response = unwrapMessage<TransportQuotationDoc[]>(await frappe.call<TransportQuotationDoc[]>(`${QUOTATION_MODULE}.get_quotation_list_with_summaries`, { limit_page_length: 500 }))
    const rows = (response ?? []).map(asRow)
    const count = (status: TransportQuotation['status']) => rows.filter((row) => row.status === status).length
    return {
      rows,
      tabs: [
        { key: 'all', label: 'All', count: rows.length },
        { key: 'draft', label: 'Draft', count: count('draft') },
        { key: 'pending_approval', label: 'Pending Approval', count: count('pending_approval') },
        { key: 'approved', label: 'Approved', count: count('approved') },
        { key: 'rejected', label: 'Rejected', count: count('rejected') },
        { key: 'cancelled', label: 'Cancelled', count: count('cancelled') },
      ],
    }
  },
  async getQuotation(name: string): Promise<TransportQuotationDoc> { return unwrap(await frappe.get<TransportQuotationDoc>('Transport Quotation', name)) },
  async getMasters(): Promise<MasterOptions> {
    const [customers, materials, locations] = await Promise.all([
      frappe.list<{ name: string; customer_name?: string }[]>('Customer', { fields: JSON.stringify(['name', 'customer_name']), filters: JSON.stringify([['disabled', '=', 0]]), limit_page_length: 500 }),
      frappe.list<{ name: string }[]>('Cargo Types', { fields: JSON.stringify(['name']), filters: JSON.stringify([['active', '=', 1]]), limit_page_length: 500 }),
      frappe.list<{ name: string; location_usage: string; area_zone?: string; city?: string }[]>('Transport Location', { fields: JSON.stringify(['name','location_usage','area_zone','city']), filters: JSON.stringify([['active', '=', 1]]), limit_page_length: 500 }),
    ])
    return {
      customers: unwrap(customers).map((x) => ({
        value: x.name,
        text: x.customer_name && x.customer_name !== x.name ? `${x.customer_name} (${x.name})` : x.name,
      })),
      materials: unwrap(materials).map((x) => x.name),
      locations: unwrap(locations).map((x) => ({
        name: x.name,
        usage: x.location_usage,
        area_zone: x.area_zone ?? '',
        city: x.city ?? '',
      })),
    }
  },
  async searchCustomers(query: string): Promise<SelectOption[]> { const response = await frappe.list<{ name: string; customer_name?: string }[]>('Customer', { fields: JSON.stringify(['name','customer_name']), or_filters: JSON.stringify([['name', 'like', `%${query}%`], ['customer_name', 'like', `%${query}%`]]), limit_page_length: 25 }); return unwrap(response).map((x) => ({ value: x.name, text: x.customer_name && x.customer_name !== x.name ? `${x.customer_name} (${x.name})` : x.name })) },
  async searchMaterials(query: string): Promise<string[]> { const response = await frappe.list<{ name: string }[]>('Cargo Types', { fields: JSON.stringify(['name']), filters: JSON.stringify([['active', '=', 1], ['name', 'like', `%${query}%`]]), limit_page_length: 25 }); return unwrap(response).map((x) => x.name) },
  async searchLocations(query: string, role?: 'Loading' | 'Destination'): Promise<SelectOption[]> {
    const usageFilter = role === 'Loading' ? ['Loading', 'Both'] : role === 'Destination' ? ['Unloading', 'Both'] : ['Loading', 'Unloading', 'Both']
    const response = await frappe.list<{ name: string; location_usage: string; area_zone?: string; city?: string }[]>('Transport Location', {
      fields: JSON.stringify(['name','location_usage','area_zone','city']),
      filters: JSON.stringify([['active', '=', 1], ['location_usage', 'in', usageFilter], ['name', 'like', `%${query}%`]]),
      limit_page_length: 50
    })
    return unwrap(response).map((x) => ({
      value: x.name,
      text: x.name,
      subtext: (x.area_zone || x.city || '').trim() || undefined,
    }))
  },
  async create(doc: TransportQuotationDoc): Promise<TransportQuotationDoc> { return unwrap(await frappe.create<TransportQuotationDoc>('Transport Quotation', doc as unknown as Record<string, unknown>)) },
  async update(name: string, doc: TransportQuotationDoc): Promise<TransportQuotationDoc> { return unwrap(await frappe.update<TransportQuotationDoc>('Transport Quotation', name, doc as unknown as Record<string, unknown>)) },
  async sendToCustomer(name: string, customerNote?: string): Promise<TransportQuotationDoc> {
    return unwrapMessage(await frappe.call<TransportQuotationDoc>(`${QUOTATION_MODULE}.send_quotation_to_customer`, { name, customer_note: customerNote ?? '' }))
  },
  async approve(name: string, approvalDate: string, approvalNotes?: string, approvalReference?: string): Promise<TransportQuotationDoc> {
    return unwrapMessage(await frappe.call<TransportQuotationDoc>(`${QUOTATION_MODULE}.approve_quotation`, {
      name,
      approval_date: approvalDate,
      approval_notes: approvalNotes ?? '',
      approval_reference: approvalReference ?? '',
    }))
  },
  async reject(name: string, rejectionReason: string): Promise<TransportQuotationDoc> {
    return unwrapMessage(await frappe.call<TransportQuotationDoc>(`${QUOTATION_MODULE}.reject_quotation`, { name, rejection_reason: rejectionReason }))
  },
  async submit(doc: TransportQuotationDoc): Promise<TransportQuotationDoc> { return unwrapMessage(await frappe.call<TransportQuotationDoc>('frappe.client.submit', { doc: JSON.stringify({ ...doc, doctype: 'Transport Quotation' }) })) },
  async cancel(name: string): Promise<TransportQuotationDoc> { return unwrapMessage(await frappe.call<TransportQuotationDoc>('frappe.client.cancel', { doctype: 'Transport Quotation', name })) },
  async createSalesOrder(name: string, areaZone?: string): Promise<string> {
    return unwrapMessage<string>(await frappe.call<string>(
      'transport_management.transport_management.doctype.transport_sales_order.transport_sales_order.create_quotation_transport_sales_order',
      { quotation: name, area_zone: areaZone ?? undefined }
    ))
  },
  async getQuotationSalesOrderSummary(name: string): Promise<QuotationSalesOrderSummaryResponse> {
    return unwrapMessage<QuotationSalesOrderSummaryResponse>(await frappe.call<QuotationSalesOrderSummaryResponse>(
      'transport_management.transport_management.doctype.transport_sales_order.transport_sales_order.get_quotation_sales_order_summary',
      { quotation: name }
    ))
  },
}
const mockExtended = {
  ...mockService,
  getQuotation: async (_name: string) => ({}) as TransportQuotationDoc,
  getMasters: async () => ({ customers: [], materials: [], locations: [] }),
  searchCustomers: async (_query: string) => [],
  searchMaterials: async (_query: string) => [],
  searchLocations: async (_query: string, _role?: 'Loading' | 'Destination') => [],
  create: async (doc: TransportQuotationDoc) => doc,
  update: async (_name: string, doc: TransportQuotationDoc) => doc,
  sendToCustomer: async (name: string, customerNote?: string) => ({ name, status: 'Pending Approval', customer_approval_notes: customerNote }) as TransportQuotationDoc,
  approve: async (name: string, approvalDate: string, approvalNotes?: string) => ({ name, status: 'Approved', docstatus: 1, customer_approval_date: approvalDate, customer_approval_notes: approvalNotes }) as TransportQuotationDoc,
  reject: async (name: string, rejectionReason: string) => ({ name, status: 'Rejected', docstatus: 0, customer_approval_notes: rejectionReason }) as TransportQuotationDoc,
  submit: async (doc: TransportQuotationDoc) => doc,
  cancel: async (_name: string) => ({}) as TransportQuotationDoc,
  createSalesOrder: async (_name: string, _areaZone?: string) => 'TSO-MOCK-001',
  getQuotationSalesOrderSummary: async (_name: string): Promise<QuotationSalesOrderSummaryResponse> => ({
    quotation: _name,
    customer: 'Mock Customer',
    status: 'Approved',
    docstatus: 1,
    total_areas: 1,
    converted_areas: 0,
    has_unconverted_areas: true,
    areas: [],
  }),
}
export const quotationsApi = apiMock ? mockExtended : frappeService
export type QuotationsService = typeof quotationsApi
export function createQuotationsService(): QuotationsService { return quotationsApi }