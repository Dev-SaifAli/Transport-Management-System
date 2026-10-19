<script setup lang="ts">
import { ArrowRight } from 'lucide-vue-next'
import { computed } from 'vue'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { FleetMapMarker, TripStatus } from '@/types/dashboard'

const props = defineProps<{ markers: FleetMapMarker[] }>()

/**
 * Stylized, illustrative fleet map.
 * Positions are mock data rendered on a static vector map — this is NOT a
 * live GPS integration.
 */
const statusColor: Record<TripStatus, string> = {
  'in-transit': '#2563eb',
  loading: '#d97706',
  scheduled: '#2563eb',
  delivered: '#059669',
  completed: '#059669',
  pending: '#d97706',
  correction: '#dc2626',
  attention: '#dc2626',
}

const positionedMarkers = computed(() =>
  props.markers.map((m) => ({
    ...m,
    cx: (m.x / 100) * 800,
    cy: (m.y / 100) * 360,
    color: statusColor[m.status],
  })),
)
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Live Fleet Map</CardTitle>
      <span class="flex items-center gap-1 text-sm font-bold text-lime-700">
        Open Live Map
        <ArrowRight class="size-4" aria-hidden="true" />
      </span>
    </CardHeader>
    <CardContent>
      <div class="relative overflow-hidden rounded-xl border bg-[#e9eff5]">
        <svg viewBox="0 0 800 360" class="block h-auto w-full" role="img" aria-label="Illustrative fleet map">
          <!-- water -->
          <path d="M0,300 C120,260 200,340 320,330 C420,322 460,360 520,360 L0,360 Z" fill="#dbe8f3" />
          <path d="M640,0 L800,0 L800,120 C740,110 700,60 640,0 Z" fill="#dbe8f3" opacity="0.7" />
          <!-- land parcels -->
          <g stroke="#dde5ec" stroke-width="1.5" fill="#eef3f7">
            <path d="M40,40 h180 v110 h-180 Z" />
            <path d="M250,30 h150 v90 h-150 Z" />
            <path d="M430,60 h170 v100 h-170 Z" />
            <path d="M60,180 h200 v90 h-200 Z" />
            <path d="M300,150 h180 v100 h-180 Z" />
            <path d="M520,190 h220 v100 h-220 Z" />
          </g>
          <!-- roads -->
          <g stroke="#ffffff" stroke-width="7" fill="none" stroke-linecap="round">
            <path d="M0,140 C150,130 320,160 480,150 C600,143 700,150 800,145" />
            <path d="M230,0 C240,120 210,240 235,360" />
            <path d="M480,0 C470,110 500,230 485,360" />
            <path d="M620,40 C580,120 660,220 610,330" />
          </g>
          <g stroke="#c9d4de" stroke-width="2" fill="none">
            <path d="M0,230 C180,220 380,250 560,235 C680,225 740,235 800,230" />
            <path d="M110,0 C120,140 90,260 115,360" />
            <path d="M340,20 C350,130 330,250 350,350" />
            <path d="M40,60 C200,70 420,40 780,70" />
          </g>
          <!-- dashed active route -->
          <path
            d="M272,223 C330,210 340,190 376,202 C420,216 470,190 544,158"
            fill="none"
            stroke="#65a30d"
            stroke-width="2.5"
            stroke-dasharray="7 6"
            stroke-linecap="round"
          />
          <!-- markers -->
          <g v-for="m in positionedMarkers" :key="m.id">
            <circle :cx="m.cx" :cy="m.cy" r="12" :fill="m.color" opacity="0.18" />
            <circle :cx="m.cx" :cy="m.cy" r="7" :fill="m.color" stroke="#ffffff" stroke-width="2.5" />
            <text
              :x="m.cx"
              :y="m.cy - 16"
              text-anchor="middle"
              font-size="12"
              font-weight="700"
              fill="#334155"
              font-family="inherit"
            >
              {{ m.id }}
            </text>
          </g>
        </svg>

        <!-- legend -->
        <div class="absolute bottom-3 left-3 flex items-center gap-4 rounded-lg bg-white/85 px-3 py-2 text-xs font-medium text-slate-700 shadow-sm backdrop-blur">
          <span class="flex items-center gap-1.5">
            <span class="size-2.5 rounded-full bg-blue-600" aria-hidden="true" /> In Transit
          </span>
          <span class="flex items-center gap-1.5">
            <span class="size-2.5 rounded-full bg-amber-600" aria-hidden="true" /> Loading
          </span>
          <span class="flex items-center gap-1.5">
            <span class="size-2.5 rounded-full bg-emerald-600" aria-hidden="true" /> Delivered
          </span>
        </div>
        <p class="absolute bottom-3 right-3 rounded bg-white/70 px-2 py-1 text-[10px] font-medium text-slate-500">
          Illustrative positions · not live GPS
        </p>
      </div>
    </CardContent>
  </Card>
</template>
