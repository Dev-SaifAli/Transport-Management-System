<script setup lang="ts">
import { Truck } from 'lucide-vue-next'

import { cn } from '@/lib/utils'

import SidebarNavigation from './SidebarNavigation.vue'

interface Props {
  collapsed: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'navigate'): void
  (e: 'toggle-collapse'): void
}>()
</script>

<template>
  <aside
    class="sticky top-0 z-30 hidden h-screen shrink-0 flex-col justify-between border-r border-border/70 bg-background transition-[width] duration-200 lg:flex"
    :class="collapsed ? 'w-[72px]' : 'w-64 xl:w-72'"
    aria-label="Sidebar"
  >
    <!-- Brand Header -->
    <div
      class="flex h-[72px] shrink-0 items-center border-b border-border/70 transition-all"
      :class="collapsed ? 'justify-center px-2' : 'px-5'"
    >
      <div class="flex items-center gap-3 min-w-0">
        <button
          type="button"
          class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#001233] text-white shadow-xs transition-all hover:bg-[#001845] hover:scale-[1.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :title="collapsed ? 'Expand sidebar ([)' : 'AL RANA Dispatch'"
          @click="collapsed ? emit('toggle-collapse') : undefined"
        >
          <Truck class="size-5 text-white" aria-hidden="true" />
        </button>
        <div v-if="!collapsed" class="min-w-0 leading-tight">
          <p class="truncate text-[15px] font-extrabold tracking-tight text-foreground">AL RANA</p>
          <p class="truncate text-xs font-medium text-muted-foreground">Dispatch Portal</p>
        </div>
      </div>
    </div>

    <!-- Navigation (flex-1 with its own overflow-y-auto) -->
    <div class="flex-1 overflow-y-auto">
      <SidebarNavigation :collapsed="collapsed" @navigate="emit('navigate')" />
    </div>

    <!-- ERPNext sync status widget pinned to bottom -->
    <div class="shrink-0 border-t border-border/60 p-3">
      <div
        class="rounded-xl border border-border/70 bg-card/60 p-3 shadow-2xs backdrop-blur-xs transition-colors hover:bg-card hover:border-border"
        :class="cn({ 'flex justify-center p-2.5': collapsed })"
        :title="collapsed ? 'ERPNext Sync — Connected · Live backend' : undefined"
      >
        <template v-if="!collapsed">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="relative flex size-2">
                <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span class="relative inline-flex size-2 rounded-full bg-emerald-500" />
              </span>
              <p class="text-xs font-bold text-foreground">ERPNext Sync</p>
            </div>
            <span class="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">Live</span>
          </div>
          <p class="mt-1 text-[11px] font-medium text-muted-foreground">Connected · Live backend</p>
        </template>
        <span v-else class="relative flex size-2">
          <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span class="relative inline-flex size-2 rounded-full bg-emerald-500" />
        </span>
      </div>
    </div>
  </aside>
</template>
