import { apiMock } from '@/config'
import { frappe } from '@/services/frappe/frappeClient'
import { mockQuotationTabs, mockQuotations } from '@/mock/quotations'
import type { QuotationTabKey, TransportQuotation, TransportQuotationDoc } from '@/types/quotations'

export interface QuotationsResponse { tabs: { key: QuotationTabKey; label: string; count: number }[]; rows: TransportQuotation[] }
export interface SelectOption { value: string; text: string }
export interface MasterOptions { customers: SelectOption[]; materials: string[]; locations: { name: string; usage: string }[] }
export interface MasterSearchApi { searchCustomers(query: string): Promise<string[]>; searchMaterials(query: string): Promise<string[]>; searchLocations(query: string, role?: 'Loading' | 'Destination'): Promise<{ name: string; usage: string }[]> }
function unwrap<T>(response: T | { data: T }): T { return (response as { data?: T }).data ?? response as T }
function unwrapMessage<T>(response: unknown): T {
  const payload = unwrap(response as T | { data: T }) as T | { message?: T }
  return (payload as { message?: T }).message ?? payload as T
}
function statusOf(doc: Partial<TransportQuotationDoc>): TransportQuotation['status'] { return doc.status === 'Approved' || doc.docstatus === 1 ? 'approved' : doc.status === 'Cancelled' || doc.docstatus === 2 ? 'cancelled' : 'draft' }
function asRow(doc: TransportQuotationDoc): TransportQuotation {
  const materials = (doc.materials ?? []).map((row) => row.material).filter(Boolean)
  const loading = new Set((doc.locations ?? []).filter((row) => row.location_role === 'Loading').map((row) => row.location)).size
  const destinations = new Set((doc.locations ?? []).filter((row) => row.location_role === 'Destination').map((row) => row.location)).size
  return { id: doc.name ?? '', customer: doc.customer, quotationDate: doc.quotation_date, validUntil: doc.valid_until, materials: materials.length ? materials.join(', ') : '—', rateLines: doc.rates?.length ?? 0, status: statusOf(doc), createdBy: doc.owner ?? '', modified: doc.modified, locationCount: loading || destinations ? `${loading} loading → ${destinations} destination` : '—' }
}
const mockService = { async getQuotations(): Promise<QuotationsResponse> { return structuredClone({ tabs: mockQuotationTabs, rows: mockQuotations }) } }
const frappeService = {
  async getQuotations(): Promise<QuotationsResponse> {
    const response = unwrap(await frappe.list<TransportQuotationDoc[]>('Transport Quotation', { fields: JSON.stringify(['name','customer','quotation_date','valid_until','status','docstatus','owner','modified','materials','locations','rates']), limit_page_length: 500 }))
    const rows = response.map(asRow); const count = (status: TransportQuotation['status']) => rows.filter((row) => row.status === status).length
    return { rows, tabs: [{ key: 'all', label: 'All', count: rows.length }, { key: 'draft', label: 'Draft', count: count('draft') }, { key: 'approved', label: 'Approved', count: count('approved') }, { key: 'cancelled', label: 'Cancelled', count: count('cancelled') }] }
  },
  async getQuotation(name: string): Promise<TransportQuotationDoc> { return unwrap(await frappe.get<TransportQuotationDoc>('Transport Quotation', name)) },
  async getMasters(): Promise<MasterOptions> {
    const [customers, materials, locations] = await Promise.all([
      frappe.list<{ name: string }[]>('Customer', { fields: JSON.stringify(['name']), limit_page_length: 500 }),
      frappe.list<{ name: string }[]>('Cargo Types', { fields: JSON.stringify(['name']), filters: JSON.stringify([['active', '=', 1]]), limit_page_length: 500 }),
      frappe.list<{ name: string; location_usage: string }[]>('Transport Location', { fields: JSON.stringify(['name','location_usage']), filters: JSON.stringify([['active', '=', 1]]), limit_page_length: 500 }),
    ])
    return { customers: unwrap(customers).map((x) => ({ value: x.name, text: x.name })), materials: unwrap(materials).map((x) => x.name), locations: unwrap(locations).map((x) => ({ name: x.name, usage: x.location_usage })) }
  },
  async searchCustomers(query: string): Promise<SelectOption[]> { const response = await frappe.list<{ name: string; customer_name?: string }[]>('Customer', { fields: JSON.stringify(['name','customer_name']), or_filters: JSON.stringify([['name', 'like', `%${query}%`], ['customer_name', 'like', `%${query}%`]]), limit_page_length: 25 }); return unwrap(response).map((x) => ({ value: x.name, text: x.customer_name && x.customer_name !== x.name ? `${x.customer_name} (${x.name})` : x.name })) },
  async searchMaterials(query: string): Promise<string[]> { const response = await frappe.list<{ name: string }[]>('Cargo Types', { fields: JSON.stringify(['name']), filters: JSON.stringify([['active', '=', 1], ['name', 'like', `%${query}%`]]), limit_page_length: 25 }); return unwrap(response).map((x) => x.name) },
  async searchLocations(query: string, role?: 'Loading' | 'Destination'): Promise<{ name: string; usage: string }[]> { const response = await frappe.list<{ name: string; location_usage: string }[]>('Transport Location', { fields: JSON.stringify(['name','location_usage']), filters: JSON.stringify([['active', '=', 1], ['name', 'like', `%${query}%`]]), limit_page_length: 50 }); return unwrap(response).filter((x) => !role || x.location_usage === 'Both' || (role === 'Loading' ? x.location_usage === 'Loading' : x.location_usage === 'Unloading')).map((x) => ({ name: x.name, usage: x.location_usage })) },
  async create(doc: TransportQuotationDoc): Promise<TransportQuotationDoc> { return unwrap(await frappe.create<TransportQuotationDoc>('Transport Quotation', doc as unknown as Record<string, unknown>)) },
  async update(name: string, doc: TransportQuotationDoc): Promise<TransportQuotationDoc> { return unwrap(await frappe.update<TransportQuotationDoc>('Transport Quotation', name, doc as unknown as Record<string, unknown>)) },
  async submit(doc: TransportQuotationDoc): Promise<TransportQuotationDoc> { return unwrapMessage(await frappe.call<TransportQuotationDoc>('frappe.client.submit', { doc: JSON.stringify({ ...doc, doctype: 'Transport Quotation' }) })) },
  async createSalesOrder(name: string): Promise<string> { return unwrapMessage<string>(await frappe.call<string>('transport_management.transport_management.doctype.transport_sales_order.transport_sales_order.create_quotation_transport_sales_order', { quotation: name })) },
}
const mockExtended = { ...mockService, getQuotation: async (_name: string) => ({}) as TransportQuotationDoc, getMasters: async () => ({ customers: [], materials: [], locations: [] }), searchCustomers: async (_query: string) => [], searchMaterials: async (_query: string) => [], searchLocations: async (_query: string, _role?: 'Loading' | 'Destination') => [], create: async (doc: TransportQuotationDoc) => doc, update: async (_name: string, doc: TransportQuotationDoc) => doc, submit: async (doc: TransportQuotationDoc) => doc, createSalesOrder: async (_name: string) => '' }
export const quotationsApi = apiMock ? mockExtended : frappeService
export type QuotationsService = typeof quotationsApi
export function createQuotationsService(): QuotationsService { return quotationsApi }
