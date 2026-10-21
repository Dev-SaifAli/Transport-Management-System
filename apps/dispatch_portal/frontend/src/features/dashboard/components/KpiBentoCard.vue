<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useAnimatedNumber } from '@/composables/useAnimatedNumber'
import { Card, CardContent } from '@/components/ui/card'

interface Props {
  title: string
  value: number | string
  subtext?: string
  badgeColor?: 'blue' | 'amber' | 'emerald' | 'rose' | 'default'
  visualType?: 'sparkline' | 'progress' | 'segmented' | 'meter'
  visualProgress?: number // 0 to 100 for progress or meter
  segmentedValues?: { label: string; count: number; colorClass: string }[]
  sparklinePoints?: number[]
  loading?: boolean
  icon?: Component
}

const props = withDefaults(defineProps<Props>(), {
  subtext: '',
  badgeColor: 'blue',
  visualType: 'sparkline',
  visualProgress: 68,
  segmentedValues: () => [
    { label: 'Assigned', count: 7, colorClass: 'bg-[#0466C8]' },
    { label: 'Unassigned', count: 3, colorClass: 'bg-amber-500' },
  ],
  sparklinePoints: () => [12, 16, 14, 22, 19, 28, 24, 32, 29, 36],
  loading: false,
})

const numericValue = computed(() => {
  if (typeof props.value === 'number') return props.value
  const parsed = parseInt(props.value, 10)
  return isNaN(parsed) ? 0 : parsed
})

const animatedNumber = useAnimatedNumber(() => numericValue.value, 700)

const isNumeric = computed(() => !isNaN(parseInt(String(props.value), 10)))

// SVG Sparkline calculation
const sparklineSvgPath = computed(() => {
  const points = props.sparklinePoints
  if (!points || points.length < 2) return { path: '', area: '' }
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  const width = 140
  const height = 40
  const padding = 4

  const coords = points.map((p, idx) => {
    const x = padding + (idx / (points.length - 1)) * (width - 2 * padding)
    const y = height - padding - ((p - min) / range) * (height - 2 * padding)
    return { x, y }
  })

  // Simple smooth path
  let path = `M ${coords[0].x} ${coords[0].y}`
  for (let i = 1; i < coords.length; i++) {
    const prev = coords[i - 1]
    const cur = coords[i]
    const cx = (prev.x + cur.x) / 2
    path += ` C ${cx} ${prev.y}, ${cx} ${cur.y}, ${cur.x} ${cur.y}`
  }

  const area = `${path} L ${coords[coords.length - 1].x} ${height} L ${coords[0].x} ${height} Z`
  return { path, area }
})

const badgeThemeClasses = computed(() => {
  switch (props.badgeColor) {
    case 'emerald':
      return {
        pill: 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20',
        dot: 'bg-emerald-500',
      }
    case 'amber':
      return {
        pill: 'bg-amber-500/10 text-amber-800 border-amber-500/25',
        dot: 'bg-amber-500',
      }
    case 'rose':
      return {
        pill: 'bg-rose-500/10 text-rose-700 border-rose-500/20',
        dot: 'bg-rose-500',
      }
    default:
      return {
        pill: 'bg-[#0466C8]/10 text-[#023E7D] border-[#0466C8]/20',
        dot: 'bg-[#0466C8]',
      }
  }
})
</script>

<template>
  <Card class="group relative overflow-hidden transition-all duration-300 hover:shadow-md hover:border-[#0466C8]/40">
    <CardContent class="p-5">
      <!-- Loading Shimmer Skeleton -->
      <div v-if="loading" class="space-y-3 animate-pulse">
        <div class="flex items-center justify-between">
          <div class="h-3.5 w-24 rounded bg-muted/80" />
          <div class="size-8 rounded-lg bg-muted/80" />
        </div>
        <div class="h-8 w-16 rounded bg-muted/80" />
        <div class="h-3 w-32 rounded bg-muted/60" />
        <div class="h-2 w-full rounded bg-muted/50 mt-2" />
      </div>

      <!-- Real Content -->
      <div v-else class="flex flex-col justify-between h-full space-y-3.5">
        <!-- Top header row: Title + Icon -->
        <div class="flex items-center justify-between">
          <p class="text-[13px] font-bold tracking-tight text-muted-foreground uppercase">
            {{ title }}
          </p>
          <div
            v-if="icon"
            class="flex size-9 items-center justify-center rounded-xl bg-muted/60 text-foreground transition-transform duration-300 group-hover:scale-105 group-hover:bg-[#0466C8]/10 group-hover:text-[#0466C8]"
          >
            <component :is="icon" class="size-4.5" aria-hidden="true" />
          </div>
        </div>

        <!-- Metric Value + Micro-Visual (Sparkline or Meter) -->
        <div class="flex items-center justify-between gap-2">
          <span class="text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">
            {{ isNumeric ? animatedNumber : value }}
          </span>

          <!-- Micro-Visual: Sparkline -->
          <div v-if="visualType === 'sparkline'" class="w-24 shrink-0 sm:w-28">
            <svg viewBox="0 0 140 40" class="w-full h-9 overflow-visible" preserveAspectRatio="none">
              <defs>
                <linearGradient id="sparkline-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#0466C8" stop-opacity="0.25" />
                  <stop offset="100%" stop-color="#0466C8" stop-opacity="0.0" />
                </linearGradient>
              </defs>
              <path :d="sparklineSvgPath.area" fill="url(#sparkline-grad)" />
              <path
                :d="sparklineSvgPath.path"
                fill="none"
                stroke="#0466C8"
                stroke-width="2.5"
                stroke-linecap="round"
                class="transition-all duration-700 ease-out"
              />
            </svg>
          </div>

          <!-- Micro-Visual: Meter / Radar Pulse Gauge -->
          <div v-else-if="visualType === 'meter'" class="flex items-center gap-2 shrink-0 pr-1">
            <div class="relative flex size-3.5 items-center justify-center">
              <span class="absolute inline-flex size-full animate-ping rounded-full bg-[#0466C8] opacity-75" />
              <span class="relative inline-flex size-2 rounded-full bg-[#0466C8]" />
            </div>
            <span class="text-xs font-bold text-[#0466C8]">Live</span>
          </div>
        </div>

        <!-- Subtext Badge -->
        <div v-if="subtext" class="flex items-center gap-1.5">
          <span
            class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold whitespace-nowrap tracking-tight"
            :class="badgeThemeClasses.pill"
          >
            <span class="size-1.5 shrink-0 rounded-full" :class="badgeThemeClasses.dot" />
            <span class="truncate">{{ subtext }}</span>
          </span>
        </div>

        <!-- Micro-Visual: Progress Bar -->
        <div v-if="visualType === 'progress'" class="pt-0.5">
          <div class="flex justify-between text-[11px] font-medium text-muted-foreground mb-1">
            <span>Fleet Utilization</span>
            <span class="font-bold text-foreground">{{ visualProgress }}%</span>
          </div>
          <div class="h-2 w-full overflow-hidden rounded-full bg-muted/80">
            <div
              class="h-full rounded-full bg-[#0466C8] transition-all duration-700 ease-out"
              :style="{ width: `${visualProgress}%` }"
            />
          </div>
        </div>

        <!-- Micro-Visual: Segmented Bar -->
        <div v-else-if="visualType === 'segmented'" class="pt-0.5 space-y-1.5">
          <div class="flex h-2 w-full overflow-hidden rounded-full bg-muted/80 gap-0.5">
            <div
              v-for="(seg, idx) in segmentedValues"
              :key="idx"
              class="h-full first:rounded-l-full last:rounded-r-full transition-all duration-700 ease-out"
              :class="seg.colorClass"
              :style="{ flexGrow: seg.count || 1 }"
              :title="`${seg.label}: ${seg.count}`"
            />
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

