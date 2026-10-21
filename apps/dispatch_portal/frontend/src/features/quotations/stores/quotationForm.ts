import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Quotation,
  QuotationMaterial,
  RateGroup,
  CargoMaterial,
  LoadingPoint,
  DeliveryDestination,
  MasterOptions,
  SelectOption,
} from '../types'
import {
  createQuotationsService,
  type QuotationsService,
  type MasterLocation,
} from '@/services/api/quotations'
import type { TransportQuotationDoc, QuotationRate } from '@/types/quotations'
import { useToastStore } from '@/stores/toast'

export function mapMaterials(materials: string[]): CargoMaterial[] {
  return materials.map((name: string) => ({ id: name, name, code: name, cargoType: name, uom: 'TON' }))
}

export function mapLocations(locations: MasterLocation[]): LoadingPoint[] {
  return locations
    .filter((l) => l.usage === 'Loading' || l.usage === 'Both')
    .map((l) => ({
      id: l.name,
      name: l.name,
      area: (l.area_zone || l.city || '').trim(),
    }))
}

export function mapDestinations(locations: MasterLocation[]): DeliveryDestination[] {
  return locations
    .filter((l) => l.usage === 'Unloading' || l.usage === 'Both')
    .map((l) => ({
      id: l.name,
      name: l.name,
      emirate: (l.area_zone || l.city || '').trim(),
      zone: (l.area_zone || '').trim() || undefined,
    }))
}

export function expandMaterialRates(m: QuotationMaterial, q: Pick<Quotation, 'quotationDate' | 'validUntil'>): QuotationRate[] {
  const rawRows: QuotationRate[] = []

  if (m.rateGroups.length > 0) {
    m.rateGroups.forEach((rg: RateGroup) => {
      const uniquePoints = Array.from(new Set(rg.loadingPointIds))
      uniquePoints.forEach((lpId) => {
        if (!lpId || !rg.destinationId) return
        rawRows.push({
          material: m.materialId,
          loading_location: lpId,
          unloading_location: rg.destinationId,
          rate: Number(rg.rate),
          effective_from: rg.effectiveFrom || q.quotationDate,
          effective_to: rg.effectiveTo || q.validUntil,
          rate_group: rg.name,
        })
      })
    })
  } else if (m.quickRate) {
    const uniquePoints = Array.from(new Set(m.selectedLoadingPointIds))
    const uniqueDests = Array.from(new Set(m.selectedDestinationIds))
    uniqueDests.forEach((destId, dIdx) => {
      const groupName = uniqueDests.length > 1 ? `Quick Rate ${dIdx + 1}` : 'Quick Rate'
      uniquePoints.forEach((lpId) => {
        if (!lpId || !destId) return
        rawRows.push({
          material: m.materialId,
          loading_location: lpId,
          unloading_location: destId,
          rate: Number(m.quickRate!.rate),
          effective_from: m.quickRate!.effectiveFrom || q.quotationDate,
          effective_to: m.quickRate!.effectiveTo || q.validUntil,
          rate_group: groupName,
        })
      })
    })
  }

  const seen = new Set<string>()
  return rawRows.filter((row) => {
    const key = `${row.material}|${row.loading_location}|${row.unloading_location}|${row.effective_from}|${row.effective_to}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export function groupRatesIntoRateGroups(
  rates: Array<{
    material: string
    rate_group?: string
    loading_location: string
    unloading_location: string
    rate: number | string
    currency?: string
    effective_from: string
    effective_to: string
  }>,
  materialId: string,
  materialIdx: number,
  defaultCurrency: string
): RateGroup[] {
  const materialRates = (rates ?? []).filter((r) => r.material === materialId)
  const grouped = new Map<string, RateGroup>()

  materialRates.forEach((r, rIdx) => {
    const rateNum = Number(r.rate)
    const groupLabel = (r.rate_group || '').trim()
    const key = groupLabel
      ? `named::${groupLabel}::${r.unloading_location}::${rateNum}::${r.effective_from}::${r.effective_to}`
      : `auto::${r.unloading_location}::${rateNum}::${r.effective_from}::${r.effective_to}`

    const existing = grouped.get(key)
    if (existing) {
      if (r.loading_location && !existing.loadingPointIds.includes(r.loading_location)) {
        existing.loadingPointIds.push(r.loading_location)
      }
      existing.isShared = existing.loadingPointIds.length > 1
    } else {
      const groupIndex = grouped.size + 1
      grouped.set(key, {
        id: `rg-${materialIdx}-${groupIndex}-${rIdx}`,
        name: groupLabel || `Rate Group ${groupIndex}`,
        loadingPointIds: r.loading_location ? [r.loading_location] : [],
        destinationId: r.unloading_location,
        rate: rateNum,
        currency: r.currency || defaultCurrency,
        effectiveFrom: r.effective_from,
        effectiveTo: r.effective_to,
        isShared: false,
      })
    }
  })

  return Array.from(grouped.values())
}

export function buildQuotationPayload(
  q: Quotation,
  approvalDate?: string,
  notesOverride?: string
): TransportQuotationDoc {
  const apiStatus: TransportQuotationDoc['status'] = q.status

  const rates = q.materials.flatMap((m: QuotationMaterial) => expandMaterialRates(m, q))

  // Compute service period so both bounds are set together and encompass rate effective dates
  let serviceFrom = q.quotationDate || ''
  let serviceTo = q.validUntil || ''
  if (serviceFrom && serviceTo) {
    rates.forEach((r) => {
      if (r.effective_from && r.effective_from < serviceFrom) serviceFrom = r.effective_from
      if (r.effective_to && r.effective_to > serviceTo) serviceTo = r.effective_to
    })
  } else {
    serviceFrom = ''
    serviceTo = ''
  }

  // Ensure locations include all selected loading points and destinations (plus any referenced in rates)
  const locations = q.materials.flatMap((m: QuotationMaterial) => {
    const matRates = rates.filter((r) => r.material === m.materialId)
    const loadingSet = new Set<string>([
      ...m.selectedLoadingPointIds,
      ...matRates.map((r) => r.loading_location),
    ])
    const destSet = new Set<string>([
      ...m.selectedDestinationIds,
      ...matRates.map((r) => r.unloading_location),
    ])
    return [
      ...Array.from(loadingSet)
        .filter(Boolean)
        .map((loc) => ({
          material: m.materialId,
          location_role: 'Loading' as const,
          location: loc,
        })),
      ...Array.from(destSet)
        .filter(Boolean)
        .map((loc) => ({
          material: m.materialId,
          location_role: 'Destination' as const,
          location: loc,
        })),
    ]
  })

  const uniqueMaterials = Array.from(
    new Set(q.materials.map((m: QuotationMaterial) => m.materialId).filter(Boolean))
  ).map((material) => ({ material }))

  return {
    quotation_date: q.quotationDate,
    customer: q.customerId || q.customerName,
    valid_until: q.validUntil,
    currency: q.currency || 'AED',
    status: apiStatus,
    customer_reference: q.customerReference,
    service_period_from: serviceFrom,
    service_period_to: serviceTo,
    revision_of: '',
    revision_reason: '',
    materials: uniqueMaterials,
    locations,
    rates,
    estimated_quantity: q.estimatedRequirement.estimatedVolume || '',
    estimated_trips: q.estimatedRequirement.estimatedTripsPerDay || '',
    customer_approval_date: approvalDate || '',
    customer_approval_reference: '',
    customer_approval_notes: notesOverride ?? q.estimatedRequirement.notes,
    customer_approval_attachment: '',
    remarks: q.remarks,
  }
}

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) {
    return err.message.replace(/^[a-zA-Z0-9_.]+Error:\s*/, '').trim() || fallback
  }
  return fallback
}

function defaultValidUntil(fromDateStr: string): string {
  try {
    const base = fromDateStr ? new Date(fromDateStr) : new Date()
    base.setDate(base.getDate() + 30)
    return base.toISOString().slice(0, 10)
  } catch {
    return ''
  }
}

export const useQuotationFormStore = defineStore('quotationForm', () => {
  const toast = useToastStore()
  let api: QuotationsService = createQuotationsService()

  function setApi(customApi: QuotationsService) {
    api = customApi
  }

  const todayStr = new Date().toISOString().slice(0, 10)
  const savedQuotationName = ref<string | null>(null)
  const isPersisted = computed(() => Boolean(savedQuotationName.value))
  const justSaved = ref(false)
  const modalError = ref<string | null>(null)

  const quotation = ref<Quotation>({
    quotationNumber: 'NEW',
    customerId: '',
    customerName: '',
    quotationDate: todayStr,
    validUntil: defaultValidUntil(todayStr),
    company: 'AL RANA TRANSPORT LLC',
    currency: 'AED',
    customerReference: '',
    remarks: '',
    status: 'Draft',
    materials: [],
    estimatedRequirement: {
      enabled: false,
      estimatedVolume: 10000,
      volumeUom: 'TON',
      truckType: 'Tipper 45m3',
      frequency: 'Daily',
      estimatedTripsPerDay: 10,
      notes: 'Planning only — estimates never limit operational trips',
    },
  })

  const displayStatus = computed(() => {
    if (quotation.value.status === 'Draft') {
      return isPersisted.value || justSaved.value ? 'Saved' : 'Draft'
    }
    return quotation.value.status
  })

  const isSaving = ref(false)
  const isSubmitting = ref(false)
  const isSendingToCustomer = ref(false)
  const isRejecting = ref(false)
  const isEditingInfo = ref(true)
  const activeRateGroupMaterialId = ref<string | null>(null)
  const previewModalOpen = ref(false)
  const submitModalOpen = ref(false)
  const sendToCustomerModalOpen = ref(false)
  const rejectModalOpen = ref(false)
  const addMaterialModalOpen = ref(false)

  const masters = ref<MasterOptions>({
    customers: [],
    materials: [],
    locations: [],
    destinations: [],
  })
  const masterLoading = ref({ customers: false, materials: false, locations: false, destinations: false })

  const customerOptions = computed((): SelectOption[] =>
    masters.value.customers
  )

  const materialOptions = computed(() =>
    masters.value.materials
  )

  const areaOptions = computed(() => {
    const areas = Array.from(
      new Set(
        masters.value.locations
          .map((p: LoadingPoint) => p.area.trim())
          .filter((a) => a.length > 0)
      )
    ).sort()
    return [
      { value: '', text: 'All areas — no filter' },
      ...areas.map((a) => ({ value: a, text: a })),
    ]
  })

  const totalMaterialsCount = computed(() => quotation.value.materials.length)

  const totalLoadingPointsCount = computed(() => {
    const uniquePoints = new Set<string>()
    quotation.value.materials.forEach((m: QuotationMaterial) => {
      m.selectedLoadingPointIds.forEach((id) => uniquePoints.add(id))
    })
    return uniquePoints.size
  })

  const totalDestinationsCount = computed(() => {
    const uniqueDests = new Set<string>()
    quotation.value.materials.forEach((m: QuotationMaterial) => {
      m.selectedDestinationIds.forEach((id) => uniqueDests.add(id))
    })
    return uniqueDests.size
  })

  const totalRateGroupsCount = computed(() =>
    quotation.value.materials.reduce(
      (sum: number, m: QuotationMaterial) =>
        sum + (m.rateGroups.length > 0 ? m.rateGroups.length : m.quickRate ? 1 : 0),
      0
    )
  )

  const summaryBarText = computed(() => {
    const mCount = quotation.value.materials.length
    if (mCount === 0) return 'Draft — quotation number is assigned automatically'
    if (mCount === 1) {
      const m = quotation.value.materials[0]
      const pts = m.selectedLoadingPointIds.length
      const areas = new Set(
        m.selectedLoadingPointIds.map((pid) => {
          const pt = masters.value.locations.find((p: LoadingPoint) => p.id === pid)
          return pt?.area || 'Area'
        })
      ).size
      const dests = m.selectedDestinationIds.length
      const rgCount = m.rateGroups.length > 0 ? m.rateGroups.length : m.quickRate ? 1 : 0

      if (rgCount === 0) {
        return `${m.materialName} · ${pts} loading points · ${dests} destinations — rate schedule pending`
      }
      return `${m.materialName} · ${pts} loading points from ${areas} areas · ${dests} destinations · ${rgCount} rate groups`
    }

    return `${mCount} materials · ${totalLoadingPointsCount.value} loading points · ${totalDestinationsCount.value} destinations · ${totalRateGroupsCount.value} rate groups`
  })

  const allRateLines = computed(() => {
    const lines: Array<{
      materialName: string
      loadingPointsNames: string
      destinationName: string
      rate: number
      currency: string
      effectiveText: string
      isShared: boolean
    }> = []

    quotation.value.materials.forEach((m: QuotationMaterial) => {
      if (m.rateGroups.length > 0) {
        m.rateGroups.forEach((rg: RateGroup) => {
          const pointNames = rg.loadingPointIds
            .map((id) => masters.value.locations.find((p: LoadingPoint) => p.id === id)?.name || id)
            .join(', ')

          const destName = masters.value.destinations.find((d: DeliveryDestination) => d.id === rg.destinationId)?.name || rg.destinationId

          const effFromFormatted = formatDateShort(rg.effectiveFrom)
          const effToFormatted = formatDateShort(rg.effectiveTo)

          lines.push({
            materialName: m.materialName,
            loadingPointsNames: pointNames || 'All selected points',
            destinationName: destName,
            rate: rg.rate,
            currency: rg.currency,
            effectiveText: `${effFromFormatted}–${effToFormatted}`,
            isShared: rg.isShared,
          })
        })
      } else if (m.quickRate && m.selectedLoadingPointIds.length > 0 && m.selectedDestinationIds.length > 0) {
        const pointNames = m.selectedLoadingPointIds
          .map((id) => masters.value.locations.find((p: LoadingPoint) => p.id === id)?.name || id)
          .join(', ')
        const effFromFormatted = formatDateShort(m.quickRate.effectiveFrom || quotation.value.quotationDate)
        const effToFormatted = formatDateShort(m.quickRate.effectiveTo || quotation.value.validUntil)
        m.selectedDestinationIds.forEach((destId) => {
          const destName = masters.value.destinations.find((d: DeliveryDestination) => d.id === destId)?.name || destId
          lines.push({
            materialName: m.materialName,
            loadingPointsNames: pointNames,
            destinationName: destName,
            rate: m.quickRate!.rate,
            currency: quotation.value.currency,
            effectiveText: `${effFromFormatted}–${effToFormatted}`,
            isShared: m.selectedLoadingPointIds.length > 1,
          })
        })
      }
    })

    return lines
  })

  function formatDateShort(dateStr: string) {
    if (!dateStr) return ''
    try {
      const d = new Date(dateStr)
      const day = String(d.getDate()).padStart(2, '0')
      const month = d.toLocaleString('en-US', { month: 'short' })
      const year = d.getFullYear()
      return `${day} ${month} ${year}`
    } catch {
      return dateStr
    }
  }

  function clearModalError() {
    modalError.value = null
  }

  async function loadMasters() {
    masterLoading.value = { customers: true, materials: true, locations: true, destinations: true }
    try {
      const data = await api.getMasters()
      masters.value = {
        customers: data.customers,
        materials: mapMaterials(data.materials),
        locations: mapLocations(data.locations),
        destinations: mapDestinations(data.locations),
      }
    } catch (e) {
      toast.error('Failed to load master data')
      console.error(e)
    } finally {
      masterLoading.value = { customers: false, materials: false, locations: false, destinations: false }
    }
  }

  async function searchCustomers(query: string) {
    masterLoading.value.customers = true
    try {
      const results = await api.searchCustomers(query)
      const existing = new Set(masters.value.customers.map((c: SelectOption) => c.value))
      results.forEach((r: SelectOption) => {
        if (!existing.has(r.value)) {
          masters.value.customers.push(r)
          existing.add(r.value)
        }
      })
    } catch (e) {
      toast.error('Failed to search customers')
    } finally {
      masterLoading.value.customers = false
    }
  }

  async function searchMaterials(query: string) {
    masterLoading.value.materials = true
    try {
      const results = await api.searchMaterials(query)
      results.forEach((name: string) => {
        if (!masters.value.materials.some((m: CargoMaterial) => m.name === name)) {
          masters.value.materials.push({ id: name, name, code: name, cargoType: name, uom: 'TON' })
        }
      })
    } catch (e) {
      toast.error('Failed to search materials')
    } finally {
      masterLoading.value.materials = false
    }
  }

  async function searchLocations(query: string, role?: 'Loading' | 'Destination') {
    masterLoading.value.locations = true
    try {
      const results = await api.searchLocations(query, role)
      results.forEach((r: SelectOption) => {
        const areaText = (r.subtext || '').trim()
        if (role === 'Destination') {
          if (!masters.value.destinations.some((d: DeliveryDestination) => d.id === r.value)) {
            masters.value.destinations.push({
              id: r.value,
              name: r.text || r.value,
              emirate: areaText,
              zone: areaText || undefined,
            })
          }
        } else {
          if (!masters.value.locations.some((l: LoadingPoint) => l.id === r.value)) {
            masters.value.locations.push({
              id: r.value,
              name: r.text || r.value,
              area: areaText,
            })
          }
        }
      })
    } catch (e) {
      toast.error('Failed to search locations')
    } finally {
      masterLoading.value.locations = false
    }
  }

  function addMaterial(materialId?: string) {
    const defaultMat = materialId
      ? materialOptions.value.find((m: CargoMaterial) => m.id === materialId)
      : materialOptions.value.find((m: CargoMaterial) => !quotation.value.materials.some((qm: QuotationMaterial) => qm.materialId === m.id)) ||
        materialOptions.value[0]

    if (!defaultMat) {
      toast.error('No material available to add')
      return
    }

    const newMaterial: QuotationMaterial = {
      id: `mat-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      materialId: defaultMat.id,
      materialName: defaultMat.name,
      cargoType: defaultMat.cargoType,
      selectedLoadingAreaFilter: '',
      selectedLoadingPointIds: [],
      selectedDestinationIds: [],
      rateGroups: [],
      isExpanded: true,
    }

    quotation.value.materials.push(newMaterial)
    activeRateGroupMaterialId.value = newMaterial.id
    toast.info(`Added ${newMaterial.materialName} to quotation`)
  }

  function removeMaterial(index: number) {
    const mat = quotation.value.materials[index]
    if (confirm(`Remove ${mat.materialName} from quotation?`)) {
      quotation.value.materials.splice(index, 1)
      toast.info(`Removed ${mat.materialName}`)
    }
  }

  function toggleLoadingPoint(matIndex: number, pointId: string) {
    const mat = quotation.value.materials[matIndex]
    if (!mat) return

    const idx = mat.selectedLoadingPointIds.indexOf(pointId)
    if (idx > -1) {
      mat.selectedLoadingPointIds.splice(idx, 1)
      mat.rateGroups.forEach((rg: RateGroup) => {
        rg.loadingPointIds = rg.loadingPointIds.filter((id) => id !== pointId)
        rg.isShared = rg.loadingPointIds.length > 1
      })
    } else {
      mat.selectedLoadingPointIds.push(pointId)
    }
  }

  function selectAllInArea(matIndex: number, area: string) {
    const mat = quotation.value.materials[matIndex]
    if (!mat) return

    const pointsInArea = masters.value.locations.filter((p: LoadingPoint) => p.area === area).map((p: LoadingPoint) => p.id)
    const allSelected = pointsInArea.every((id) => mat.selectedLoadingPointIds.includes(id))

    if (allSelected) {
      mat.selectedLoadingPointIds = mat.selectedLoadingPointIds.filter((id) => !pointsInArea.includes(id))
      mat.rateGroups.forEach((rg: RateGroup) => {
        rg.loadingPointIds = rg.loadingPointIds.filter((id) => !pointsInArea.includes(id))
        rg.isShared = rg.loadingPointIds.length > 1
      })
    } else {
      pointsInArea.forEach((id) => {
        if (!mat.selectedLoadingPointIds.includes(id)) {
          mat.selectedLoadingPointIds.push(id)
        }
      })
    }
  }

  function toggleDestination(matIndex: number, destId: string) {
    const mat = quotation.value.materials[matIndex]
    if (!mat) return

    const idx = mat.selectedDestinationIds.indexOf(destId)
    if (idx > -1) {
      mat.selectedDestinationIds.splice(idx, 1)
    } else {
      mat.selectedDestinationIds.push(destId)
    }
  }

  function addRateGroup(matIndex: number) {
    const mat = quotation.value.materials[matIndex]
    if (!mat) return

    const newGroupNum = mat.rateGroups.length + 1
    // Prefer a selected destination not yet assigned to a rate group, or fallback to first destination
    const coveredDestinations = new Set(mat.rateGroups.map((rg) => rg.destinationId))
    const uncoveredDest = mat.selectedDestinationIds.find((dId) => !coveredDestinations.has(dId))
    const dest = uncoveredDest || mat.selectedDestinationIds[0] || masters.value.destinations[0]?.id || ''

    // Find loading points not yet assigned for the chosen destination, or use all selected loading points
    const coveredPointsForDest = new Set(
      mat.rateGroups
        .filter((rg) => rg.destinationId === dest)
        .flatMap((rg) => rg.loadingPointIds)
    )
    const uncoveredPoints = mat.selectedLoadingPointIds.filter((pId) => !coveredPointsForDest.has(pId))
    const points = uncoveredPoints.length > 0 ? [...uncoveredPoints] : [...mat.selectedLoadingPointIds]

    const defaultRate = mat.quickRate?.rate ?? 20.0
    const defaultFrom = mat.quickRate?.effectiveFrom || quotation.value.quotationDate
    const defaultTo = mat.quickRate?.effectiveTo || quotation.value.validUntil

    if (mat.quickRate) {
      delete mat.quickRate
    }

    const newRg: RateGroup = {
      id: `rg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      name: `Rate Group ${newGroupNum}`,
      loadingPointIds: points,
      destinationId: dest,
      rate: defaultRate,
      currency: quotation.value.currency,
      effectiveFrom: defaultFrom,
      effectiveTo: defaultTo,
      isShared: points.length > 1,
    }

    mat.rateGroups.push(newRg)
    toast.info(`Rate Group ${newGroupNum} added for ${mat.materialName}`)
  }

  function removeRateGroup(matIndex: number, groupIndex: number) {
    const mat = quotation.value.materials[matIndex]
    if (!mat) return
    mat.rateGroups.splice(groupIndex, 1)
    toast.info('Rate group removed')
  }

  function duplicateRateGroup(matIndex: number, groupIndex: number) {
    const mat = quotation.value.materials[matIndex]
    if (!mat) return
    const orig = mat.rateGroups[groupIndex]
    const clone: RateGroup = {
      ...JSON.parse(JSON.stringify(orig)),
      id: `rg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      name: `${orig.name} (Copy)`,
    }
    mat.rateGroups.splice(groupIndex + 1, 0, clone)
    toast.info(`Duplicated ${orig.name}`)
  }

  function loadPreset(
    preset: 'empty' | 'cement-started' | 'cement-rates' | 'two-materials'
  ) {
    if (preset === 'empty') {
      const today = new Date().toISOString().slice(0, 10)
      savedQuotationName.value = null
      justSaved.value = false
      modalError.value = null
      quotation.value = {
        quotationNumber: 'NEW',
        customerId: '',
        customerName: '',
        quotationDate: today,
        validUntil: defaultValidUntil(today),
        company: 'AL RANA TRANSPORT LLC',
        currency: 'AED',
        customerReference: '',
        remarks: '',
        status: 'Draft',
        materials: [],
        estimatedRequirement: {
          enabled: false,
          estimatedVolume: 10000,
          volumeUom: 'TON',
          truckType: 'Tipper 45m3',
          frequency: 'Daily',
          estimatedTripsPerDay: 10,
          notes: 'Planning only — estimates never limit operational trips',
        },
      }
      activeRateGroupMaterialId.value = null
      isEditingInfo.value = true
    }
  }

  function buildPayload(approvalDate?: string, notesOverride?: string): TransportQuotationDoc {
    return buildQuotationPayload(quotation.value, approvalDate, notesOverride)
  }

  async function persistQuotation(approvalDate?: string, notesOverride?: string): Promise<TransportQuotationDoc> {
    const doc = buildPayload(approvalDate, notesOverride)
    const existingName = savedQuotationName.value
    let result: TransportQuotationDoc
    if (existingName) {
      result = await api.update(existingName, { ...doc, name: existingName })
    } else {
      result = await api.create(doc)
    }
    const resolvedName = result?.name || existingName
    if (resolvedName) {
      savedQuotationName.value = resolvedName
      quotation.value.quotationNumber = resolvedName
    }
    return { ...doc, ...result, name: resolvedName || quotation.value.quotationNumber }
  }

  async function saveDraft(): Promise<TransportQuotationDoc | null> {
    if (isSaving.value) return null
    isSaving.value = true
    modalError.value = null
    try {
      const prevStatus = quotation.value.status
      const result = await persistQuotation()
      quotation.value.quotationNumber = result.name || quotation.value.quotationNumber
      quotation.value.status =
        result.status === 'Pending Approval' || prevStatus === 'Pending Approval'
          ? 'Pending Approval'
          : 'Draft'
      justSaved.value = true
      toast.success(`Quotation ${quotation.value.quotationNumber} saved`)
      return result
    } catch (e) {
      const msg = extractErrorMessage(e, 'Error saving quotation')
      modalError.value = msg
      toast.error(msg)
      console.error(e)
      return null
    } finally {
      isSaving.value = false
    }
  }

  async function sendToCustomer(customerNote?: string) {
    if (isSendingToCustomer.value) return
    isSendingToCustomer.value = true
    modalError.value = null
    try {
      const saved = await persistQuotation(undefined, customerNote)
      const targetName = saved.name || savedQuotationName.value || quotation.value.quotationNumber
      const final =
        typeof api.sendToCustomer === 'function'
          ? await api.sendToCustomer(targetName, customerNote)
          : saved
      const resolvedName = final?.name || targetName
      if (resolvedName) {
        savedQuotationName.value = resolvedName
        quotation.value.quotationNumber = resolvedName
      }
      quotation.value.status = 'Pending Approval'
      sendToCustomerModalOpen.value = false
      toast.success(`Quotation ${quotation.value.quotationNumber} sent to customer (Pending Approval)`)
    } catch (e) {
      const msg = extractErrorMessage(e, 'Error sending quotation to customer')
      modalError.value = msg
      toast.error(msg)
      console.error(e)
    } finally {
      isSendingToCustomer.value = false
    }
  }

  async function submitForApproval(approvalDate: string, approverNote?: string) {
    if (isSubmitting.value) return
    isSubmitting.value = true
    modalError.value = null
    try {
      const saved = await persistQuotation(approvalDate, approverNote)
      const targetName = saved.name || savedQuotationName.value || quotation.value.quotationNumber
      const final =
        typeof api.approve === 'function'
          ? await api.approve(targetName, approvalDate, approverNote, quotation.value.customerReference)
          : await api.submit(saved)
      const resolvedName = final?.name || targetName
      if (resolvedName) {
        savedQuotationName.value = resolvedName
        quotation.value.quotationNumber = resolvedName
      }
      quotation.value.status = 'Approved'
      submitModalOpen.value = false
      toast.success(`Quotation ${quotation.value.quotationNumber} marked as Customer Approved`)
    } catch (e) {
      const msg = extractErrorMessage(e, 'Error marking quotation as approved')
      modalError.value = msg
      toast.error(msg)
      console.error(e)
    } finally {
      isSubmitting.value = false
    }
  }

  async function rejectQuotation(rejectionReason?: string) {
    if (isRejecting.value) return
    isRejecting.value = true
    modalError.value = null
    try {
      const reason = (rejectionReason || 'Customer declined the quotation terms.').trim()
      const saved = await persistQuotation(undefined, reason)
      const targetName = saved.name || savedQuotationName.value || quotation.value.quotationNumber
      const final =
        typeof api.reject === 'function'
          ? await api.reject(targetName, reason)
          : await api.cancel(targetName)
      const resolvedName = final?.name || targetName
      if (resolvedName) {
        savedQuotationName.value = resolvedName
        quotation.value.quotationNumber = resolvedName
      }
      quotation.value.status = 'Rejected'
      rejectModalOpen.value = false
      toast.success(`Quotation ${quotation.value.quotationNumber} marked as Customer Rejected`)
    } catch (e) {
      const msg = extractErrorMessage(e, 'Error rejecting quotation')
      modalError.value = msg
      toast.error(msg)
      console.error(e)
    } finally {
      isRejecting.value = false
    }
  }

  async function loadExisting(id: string) {
    isSaving.value = true
    modalError.value = null
    try {
      const doc = await api.getQuotation(id)
      const docName = doc.name || id
      savedQuotationName.value = docName
      justSaved.value = true

      if (doc.customer && !masters.value.customers.some((c) => c.value === doc.customer)) {
        masters.value.customers.push({ value: doc.customer, text: doc.customer })
      }
      ;(doc.materials ?? []).forEach((m) => {
        if (m.material && !masters.value.materials.some((mat) => mat.id === m.material)) {
          masters.value.materials.push({
            id: m.material,
            name: m.material,
            code: m.material,
            cargoType: m.material,
            uom: 'TON',
          })
        }
      })
      ;(doc.locations ?? []).forEach((l) => {
        if (l.location_role === 'Loading' && !masters.value.locations.some((pt) => pt.id === l.location)) {
          masters.value.locations.push({ id: l.location, name: l.location, area: '' })
        }
        if (l.location_role === 'Destination' && !masters.value.destinations.some((dst) => dst.id === l.location)) {
          masters.value.destinations.push({ id: l.location, name: l.location, emirate: '' })
        }
      })

      const customerEntry = masters.value.customers.find((c) => c.value === doc.customer)

      quotation.value = {
        quotationNumber: docName,
        customerId: doc.customer,
        customerName: customerEntry?.text || doc.customer,
        quotationDate: doc.quotation_date,
        validUntil: doc.valid_until,
        company: 'AL RANA TRANSPORT LLC',
        currency: doc.currency || 'AED',
        customerReference: doc.customer_reference || '',
        remarks: doc.remarks || '',
        status:
          doc.status === 'Approved' || doc.docstatus === 1
            ? 'Approved'
            : doc.status === 'Rejected' || doc.status === 'Cancelled' || doc.docstatus === 2
              ? 'Rejected'
              : doc.status === 'Pending Approval'
                ? 'Pending Approval'
                : 'Draft',
        materials: (doc.materials ?? []).map((m: { material: string }, idx: number) => ({
          id: `mat-${idx}`,
          materialId: m.material,
          materialName: m.material,
          cargoType: m.material,
          selectedLoadingAreaFilter: '',
          selectedLoadingPointIds: (doc.locations ?? [])
            .filter((l: { material: string; location_role: string; location: string }) => l.material === m.material && l.location_role === 'Loading')
            .map((l: { location: string }) => l.location),
          selectedDestinationIds: (doc.locations ?? [])
            .filter((l: { material: string; location_role: string; location: string }) => l.material === m.material && l.location_role === 'Destination')
            .map((l: { location: string }) => l.location),
          rateGroups: groupRatesIntoRateGroups(doc.rates ?? [], m.material, idx, doc.currency || 'AED'),
          isExpanded: true,
        })),
        estimatedRequirement: {
          enabled: false,
          estimatedVolume: Number(doc.estimated_quantity) || 10000,
          volumeUom: 'TON',
          truckType: 'Tipper 45m3',
          frequency: 'Daily',
          estimatedTripsPerDay: Number(doc.estimated_trips) || 10,
          notes: doc.customer_approval_notes || 'Planning only — estimates never limit operational trips',
        },
      }
      if (quotation.value.materials.length > 0) {
        activeRateGroupMaterialId.value = quotation.value.materials[0].id
      }
      isEditingInfo.value = false
    } catch (e) {
      toast.error('Failed to load quotation')
      console.error(e)
    } finally {
      isSaving.value = false
    }
  }

  return {
    quotation,
    savedQuotationName,
    isPersisted,
    justSaved,
    displayStatus,
    modalError,
    isSaving,
    isSubmitting,
    isSendingToCustomer,
    isRejecting,
    isEditingInfo,
    activeRateGroupMaterialId,
    previewModalOpen,
    submitModalOpen,
    sendToCustomerModalOpen,
    rejectModalOpen,
    addMaterialModalOpen,
    masters,
    masterLoading,
    customerOptions,
    materialOptions,
    areaOptions,
    totalMaterialsCount,
    totalLoadingPointsCount,
    totalDestinationsCount,
    totalRateGroupsCount,
    summaryBarText,
    allRateLines,
    clearModalError,
    setApi,
    loadMasters,
    searchCustomers,
    searchMaterials,
    searchLocations,
    addMaterial,
    removeMaterial,
    toggleLoadingPoint,
    selectAllInArea,
    toggleDestination,
    addRateGroup,
    removeRateGroup,
    duplicateRateGroup,
    loadPreset,
    buildPayload,
    saveDraft,
    sendToCustomer,
    submitForApproval,
    rejectQuotation,
    loadExisting,
    formatDateShort,
  }
})