<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'
import { Bell, Menu, PanelLeftClose, PanelLeftOpen, RefreshCw, Search } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Props {
  sidebarOpen: boolean
  sidebarCollapsed?: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void
  (e: 'toggle-collapse'): void
  (e: 'refresh'): void
}>()

const searchInputRef = ref<any>(null)
const isSpinning = ref(false)

function handleRefresh() {
  isSpinning.value = true
  emit('refresh')
  setTimeout(() => {
    isSpinning.value = false
  }, 900)
}

const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.userAgent)
const shortcutKey = computed(() => (isMac ? '⌘K' : 'Ctrl K'))

onKeyStroke(['k', 'K'], (e) => {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    const el = searchInputRef.value?.$el ?? searchInputRef.value
    if (el && typeof el.focus === 'function') {
      el.focus()
    } else if (el?.querySelector) {
      el.querySelector('input')?.focus()
    }
  }
})
</script>

<template>
  <header class="sticky top-0 z-30 flex h-[72px] items-center gap-3 border-b border-border/70 bg-card/90 backdrop-blur-md px-4 sm:px-6">
    <!-- Mobile sidebar toggle -->
    <Button
      variant="ghost"
      size="icon"
      class="rounded-full lg:hidden"
      aria-label="Toggle navigation menu"
      :aria-expanded="sidebarOpen"
      @click="emit('toggle-sidebar')"
    >
      <Menu class="size-5" aria-hidden="true" />
    </Button>

    <!-- Desktop sidebar collapse / expand toggle -->
    <Button
      variant="ghost"
      size="icon"
      class="hidden size-9 rounded-full border border-border/70 bg-card text-muted-foreground shadow-xs transition-all hover:bg-muted/70 hover:text-foreground lg:inline-flex"
      :aria-label="sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      :title="sidebarCollapsed ? 'Expand sidebar ([)' : 'Collapse sidebar ([)'"
      @click="emit('toggle-collapse')"
    >
      <PanelLeftOpen v-if="sidebarCollapsed" class="size-4" aria-hidden="true" />
      <PanelLeftClose v-else class="size-4" aria-hidden="true" />
    </Button>

    <!-- Global search -->
    <div class="relative w-full max-w-md">
      <Search
        class="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        ref="searchInputRef"
        type="search"
        placeholder="Search trips, jobs, trucks…"
        class="h-10 rounded-full border-border/70 bg-muted/50 pl-10 pr-16 text-sm shadow-xs transition-all placeholder:text-muted-foreground/70 hover:bg-muted/80 focus:border-border focus:bg-card focus:ring-2 focus:ring-primary/20"
        aria-label="Search"
      />
      <kbd
        class="pointer-events-none absolute right-3 top-1/2 flex h-5 -translate-y-1/2 items-center gap-0.5 rounded-full border border-border/80 bg-card px-2 font-sans text-[10px] font-bold text-muted-foreground shadow-xs"
        aria-hidden="true"
      >
        {{ shortcutKey }}
      </kbd>
    </div>

    <div class="ml-auto flex items-center gap-2">
      <Button
        variant="ghost"
        size="icon"
        class="size-9 rounded-full border border-border/70 bg-card text-muted-foreground shadow-xs transition-all hover:bg-muted/70 hover:text-foreground"
        aria-label="Refresh data"
        title="Refresh data"
        @click="handleRefresh"
      >
        <RefreshCw class="size-4" :class="{ 'animate-spin': isSpinning }" aria-hidden="true" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        class="relative size-9 rounded-full border border-border/70 bg-card text-muted-foreground shadow-xs transition-all hover:bg-muted/70 hover:text-foreground"
        aria-label="Notifications"
        title="Notifications"
      >
        <Bell class="size-4" aria-hidden="true" />
        <span class="absolute right-2 top-2 size-2 rounded-full bg-rose-500 ring-2 ring-card" aria-hidden="true" />
      </Button>
      <Avatar class="ml-1 size-9 ring-2 ring-border/80" aria-label="User: SR">
        <AvatarFallback class="bg-[#001233] text-xs font-bold text-white">SR</AvatarFallback>
      </Avatar>
    </div>
  </header>
</template>
