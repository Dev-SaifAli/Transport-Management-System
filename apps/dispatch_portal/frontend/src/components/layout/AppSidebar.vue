<script setup lang="ts">
import { Truck } from 'lucide-vue-next'

import { cn } from '@/lib/utils'

import SidebarNavigation from './SidebarNavigation.vue'

interface Props {
  collapsed: boolean
}

defineProps<Props>()

const emit = defineEmits<{ (e: 'navigate'): void }>()
</script>

<template>
  <aside
    class="hidden h-screen shrink-0 flex-col border-r bg-card transition-[width] duration-200 lg:flex"
    :class="collapsed ? 'w-[76px]' : 'w-64 xl:w-72'"
    aria-label="Sidebar"
  >
    <!-- Brand -->
    <div class="flex h-[72px] items-center gap-3 border-b px-5">
      <div class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary shadow-sm">
        <Truck class="size-5 text-primary-foreground" aria-hidden="true" />
      </div>
      <div v-if="!collapsed" class="leading-tight">
        <p class="text-[15px] font-extrabold tracking-tight">AL RANA</p>
        <p class="text-xs text-muted-foreground">Dispatch Portal</p>
      </div>
    </div>

    <SidebarNavigation :collapsed="collapsed" @navigate="emit('navigate')" />

    <!-- ERPNext sync status -->
    <div class="p-3">
      <div
        class="rounded-xl border border-lime-200 bg-lime-50 p-3.5"
        :class="cn({ 'flex justify-center p-3': collapsed })"
        :title="collapsed ? 'ERPNext Sync — Connected' : undefined"
      >
        <template v-if="!collapsed">
          <div class="flex items-center gap-2">
            <span class="size-2 rounded-full bg-emerald-500" aria-hidden="true" />
            <p class="text-sm font-bold">ERPNext Sync</p>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">Connected · synced 2 min ago</p>
        </template>
        <span v-else class="size-2 rounded-full bg-emerald-500" aria-hidden="true" />
      </div>
    </div>
  </aside>
</template>
