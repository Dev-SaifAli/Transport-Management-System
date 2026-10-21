<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ExternalLink, LocateFixed, Minus, Plus } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { FleetMapMarker } from '@/types/dashboard'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface Props {
  markers?: FleetMapMarker[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  markers: () => [],
  loading: false,
})

const router = useRouter()
const mapContainerRef = ref<HTMLDivElement | null>(null)
let mapInstance: L.Map | null = null
let markerLayerGroup: L.LayerGroup | null = null

const activeFilter = ref<'all' | 'in-transit' | 'loading' | 'delivered'>('all')

// UAE Coordinate Knowledge Dictionary for Smart Fallback
const UAE_LOCATIONS: Record<string, [number, number]> = {
  // Sajja / Sharjah
  'sajja': [25.3088, 55.6540],
  'sajja oryx': [25.3088, 55.6540],
  'oryx concrete product llc sajja': [25.3088, 55.6540],
  'oryx mix concrete manufacturing llc': [25.3120, 55.6600],
  'sharjah': [25.3463, 55.4209],

  // Taween / Fujairah / Masafi
  'atbt al taween': [25.5683, 56.0711],
  'taween': [25.5683, 56.0711],
  'fujairah': [25.1288, 56.3265],
  'fujairah port': [25.1764, 56.3639],
  'masafi': [25.3167, 56.1667],
  'masafi crusher': [25.3167, 56.1667],

  // Dubai / Jebel Ali
  'dubai': [25.2048, 55.2708],
  'al quoz': [25.1372, 55.2427],
  'jebel ali': [24.9857, 55.0273],
  'jebel ali port': [24.9857, 55.0273],
  'ras al khor': [25.1833, 55.3333],

  // Abu Dhabi
  'abu dhabi': [24.4539, 54.3773],
  'mussafah': [24.3644, 54.4981],
  'icad': [24.3214, 54.4756],

  // RAK & Northern Emirates
  'rak': [25.6741, 55.9804],
  'rak plant': [25.2667, 56.0167],
  'kadra': [25.0417, 56.0417],
  'ajman': [25.4052, 55.5136],
  'umm al quwain': [25.5269, 55.5533],
}

function resolveCoordinates(name?: string, index: number = 0): [number, number] {
  if (!name) {
    return [25.3088 + (index % 4) * 0.05, 55.6540 + (index % 5) * 0.07]
  }

  const clean = name.toLowerCase().trim()
  for (const [key, coords] of Object.entries(UAE_LOCATIONS)) {
    if (clean.includes(key)) {
      // Add slight jitter to avoid exact overlapping markers
      const jitterLat = ((index * 13) % 7 - 3) * 0.003
      const jitterLng = ((index * 17) % 7 - 3) * 0.003
      return [coords[0] + jitterLat, coords[1] + jitterLng]
    }
  }

  // Fallback centered along Sharjah - Fujairah industrial corridor
  const jitterLat = ((index * 11) % 10 - 5) * 0.02
  const jitterLng = ((index * 13) % 10 - 5) * 0.03
  return [25.3200 + jitterLat, 55.7000 + jitterLng]
}

function initLeafletMap() {
  if (!mapContainerRef.value || mapInstance) return

  // Center on UAE Corridor
  const defaultCenter: [number, number] = [25.2800, 55.8500]
  const defaultZoom = 9

  mapInstance = L.map(mapContainerRef.value, {
    center: defaultCenter,
    zoom: defaultZoom,
    zoomControl: false,
    attributionControl: false,
  })

  // OpenStreetMap Clean Enterprise Tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    subdomains: 'abc',
  }).addTo(mapInstance)

  markerLayerGroup = L.layerGroup().addTo(mapInstance)
  renderMarkers()
}

function renderMarkers() {
  const layerGroup = markerLayerGroup
  if (!mapInstance || !layerGroup) return
  layerGroup.clearLayers()

  const markersToDisplay = props.markers.filter((m) => {
    if (activeFilter.value === 'all') return true
    return m.status === activeFilter.value
  })

  const bounds: L.LatLngTuple[] = []

  markersToDisplay.forEach((marker, index) => {
    // Resolve lat/lng or use UAE smart fallback
    const coords: [number, number] =
      marker.lat && marker.lng
        ? [marker.lat, marker.lng]
        : resolveCoordinates(marker.label || marker.tripId || marker.id, index)

    bounds.push(coords)

    // Marker theme colors based on status
    let pulseColor = 'bg-[#0466C8]'
    let dotColor = 'bg-[#0466C8]'
    if (marker.status === 'in-transit') {
      pulseColor = 'bg-blue-500'
      dotColor = 'bg-[#0466C8]'
    } else if (marker.status === 'loading') {
      pulseColor = 'bg-amber-400'
      dotColor = 'bg-amber-500'
    } else if (marker.status === 'delivered') {
      pulseColor = 'bg-emerald-400'
      dotColor = 'bg-emerald-600'
    }

    const customIcon = L.divIcon({
      className: 'custom-fleet-marker',
      html: `
        <div class="relative flex items-center justify-center cursor-pointer group" style="width: 32px; height: 32px;">
          <span class="absolute inline-flex size-7 animate-ping rounded-full ${pulseColor} opacity-75"></span>
          <div class="relative flex size-6 items-center justify-center rounded-full ${dotColor} text-white shadow-md ring-2 ring-white">
            <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"></path>
              <path d="M15 18H9"></path>
              <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"></path>
              <circle cx="17" cy="18" r="2"></circle>
              <circle cx="7" cy="18" r="2"></circle>
            </svg>
          </div>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
      popupAnchor: [0, -16],
    })

    const displayTripId = marker.tripId || marker.id
    const popupHtml = `
      <div class="p-2 space-y-1.5 font-sans min-w-[190px]">
        <div class="flex items-center justify-between gap-2 border-b border-slate-200 pb-1">
          <span class="font-mono text-xs font-bold text-slate-900">${displayTripId}</span>
          <span class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
            marker.status === 'in-transit' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
          }">${marker.status}</span>
        </div>
        <p class="text-xs font-semibold text-slate-800">${marker.label || 'Active Transport'}</p>
        <p class="text-[11px] text-slate-500">${marker.truck || 'Vehicle assigned'}</p>
        <button
          type="button"
          class="w-full mt-1.5 rounded-md bg-[#0466C8] px-2 py-1 text-center text-xs font-bold text-white transition hover:bg-[#0353A4] cursor-pointer"
          onclick="window.dispatchEvent(new CustomEvent('portal-navigate-trip', { detail: '${displayTripId}' }))"
        >
          View on Dispatch Board
        </button>
      </div>
    `

    const leafletMarker = L.marker(coords, { icon: customIcon })
      .bindPopup(popupHtml, { closeButton: false, offset: [0, -8] })
      .addTo(layerGroup)

    leafletMarker.on('mouseover', () => leafletMarker.openPopup())
  })

  // Fit bounds if we have valid coordinates
  if (bounds.length > 0 && mapInstance) {
    try {
      mapInstance.fitBounds(L.latLngBounds(bounds), { padding: [30, 30], maxZoom: 11 })
    } catch (e) {
      // Ignore if bounds are identical
    }
  }
}

function zoomIn() {
  mapInstance?.zoomIn()
}

function zoomOut() {
  mapInstance?.zoomOut()
}

function resetView() {
  mapInstance?.setView([25.2800, 55.8500], 9)
}

function onTripNavigate(e: Event) {
  const customEv = e as CustomEvent<string>
  if (customEv.detail) {
    router.push({
      path: '/dispatch-board',
      query: { search: customEv.detail },
    })
  }
}

onMounted(async () => {
  await nextTick()
  initLeafletMap()
  window.addEventListener('portal-navigate-trip', onTripNavigate)
})

onBeforeUnmount(() => {
  window.removeEventListener('portal-navigate-trip', onTripNavigate)
  // CRITICAL: Cleanly destroy Leaflet instance to prevent SPA memory leak and remount issues
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
    markerLayerGroup = null
  }
})

watch(
  () => props.markers,
  () => {
    renderMarkers()
  },
  { deep: true },
)

watch(activeFilter, () => {
  renderMarkers()
})
</script>

<template>
  <Card class="flex flex-col h-full overflow-hidden">
    <!-- Header -->
    <CardHeader class="flex items-center justify-between border-b border-border/70 pb-3">
      <div class="flex items-center gap-2">
        <CardTitle class="text-base font-bold tracking-tight text-foreground">
          Live Fleet Telemetry
        </CardTitle>
        <span class="relative flex size-2">
          <span class="absolute inline-flex size-full animate-ping rounded-full bg-[#0466C8] opacity-75" />
          <span class="relative inline-flex size-2 rounded-full bg-[#0466C8]" />
        </span>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          class="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition cursor-pointer"
          title="Reset map view"
          @click="resetView"
        >
          <LocateFixed class="size-4" />
        </button>
        <RouterLink
          to="/dispatch-board"
          class="inline-flex items-center gap-1 text-xs font-bold text-foreground transition-colors hover:text-[#0466C8]"
        >
          <span>Full Board</span>
          <ExternalLink class="size-3.5" aria-hidden="true" />
        </RouterLink>
      </div>
    </CardHeader>

    <!-- Map Canvas with Floating Controls -->
    <CardContent class="p-0 relative flex-1 min-h-[380px] bg-muted/20">
      <!-- Leaflet Container -->
      <div ref="mapContainerRef" class="w-full h-full min-h-[380px] z-10" />

      <!-- Floating Zoom Controls -->
      <div class="absolute right-3 top-3 z-20 flex flex-col gap-1 rounded-xl border border-border/80 bg-card/90 backdrop-blur-md p-1 shadow-md">
        <button
          type="button"
          class="flex size-7 items-center justify-center rounded-lg text-foreground transition-colors hover:bg-muted cursor-pointer"
          title="Zoom in"
          @click="zoomIn"
        >
          <Plus class="size-3.5" />
        </button>
        <div class="h-px w-full bg-border/60" />
        <button
          type="button"
          class="flex size-7 items-center justify-center rounded-lg text-foreground transition-colors hover:bg-muted cursor-pointer"
          title="Zoom out"
          @click="zoomOut"
        >
          <Minus class="size-3.5" />
        </button>
      </div>

      <!-- Floating Filter Legend at Bottom -->
      <div class="absolute bottom-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border/80 bg-card/90 backdrop-blur-md px-3 py-1.5 shadow-md">
        <div class="flex items-center gap-2 text-[11px] font-semibold text-muted-foreground">
          <span class="flex items-center gap-1">
            <span class="size-2 rounded-full bg-[#0466C8]" />
            In Transit
          </span>
          <span class="flex items-center gap-1">
            <span class="size-2 rounded-full bg-amber-500" />
            Loading
          </span>
          <span class="flex items-center gap-1">
            <span class="size-2 rounded-full bg-emerald-600" />
            Delivered
          </span>
        </div>

        <span class="text-[10px] font-mono text-muted-foreground/70 hidden sm:inline">
          {{ markers.length }} active GPS signals
        </span>
      </div>
    </CardContent>
  </Card>
</template>

<style>
/* Leaflet custom marker overrides */
.custom-fleet-marker {
  background: transparent;
  border: none;
}
.leaflet-popup-content-wrapper {
  border-radius: 0.75rem;
  box-shadow: 0 10px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
  border: 1px solid rgba(0, 0, 0, 0.08);
}
.leaflet-popup-content {
  margin: 0;
  line-height: normal;
}
</style>
