<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
import SidebarNavigation from './SidebarNavigation.vue'

const collapsed = ref(false)
const mobileOpen = ref(false)

const route = useRoute()
watch(() => route.fullPath, () => {
  mobileOpen.value = false
})

// Collapse/expand the desktop sidebar with "[" or "Ctrl+B" for keyboard users.
onKeyStroke(['[', 'b', 'B'], (e) => {
  if (e.key === '[' || ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B'))) {
    e.preventDefault()
    collapsed.value = !collapsed.value
  }
})
</script>

<template>
  <div class="flex min-h-screen bg-background">
    <AppSidebar
      :collapsed="collapsed"
      @toggle-collapse="collapsed = !collapsed"
    />

    <!-- Mobile sidebar drawer -->
    <Teleport to="body">
      <div v-if="mobileOpen" class="fixed inset-0 z-40 lg:hidden">
        <div class="absolute inset-0 bg-foreground/30" aria-hidden="true" @click="mobileOpen = false" />
        <aside class="absolute inset-y-0 left-0 flex w-72 flex-col bg-background border-r border-border/70 shadow-xl" role="dialog" aria-label="Navigation menu">
          <div class="flex h-[72px] items-center gap-3 border-b border-border/70 px-5">
            <div class="flex size-10 items-center justify-center rounded-xl bg-neutral-900 text-white shadow-xs">
              <span class="text-sm font-extrabold text-white">AR</span>
            </div>
            <div class="leading-tight">
              <p class="text-[15px] font-extrabold tracking-tight text-foreground">AL RANA</p>
              <p class="text-xs font-medium text-muted-foreground">Dispatch Portal</p>
            </div>
          </div>
          <SidebarNavigation :collapsed="false" @navigate="mobileOpen = false" />
        </aside>
      </div>
    </Teleport>

    <div class="flex min-w-0 flex-1 flex-col">
      <AppHeader
        :sidebar-open="mobileOpen"
        :sidebar-collapsed="collapsed"
        @toggle-sidebar="mobileOpen = !mobileOpen"
        @toggle-collapse="collapsed = !collapsed"
        @refresh="$emit('refresh')"
      />
      <slot />
    </div>
  </div>
</template>
