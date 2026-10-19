<script setup lang="ts">
import { Bell, Menu, RefreshCw, Search } from 'lucide-vue-next'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Props {
  sidebarOpen: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void
  (e: 'refresh'): void
}>()
</script>

<template>
  <header class="sticky top-0 z-30 flex h-[72px] items-center gap-3 border-b bg-card px-4 sm:px-6">
    <!-- Mobile sidebar toggle -->
    <Button
      variant="ghost"
      size="icon"
      class="lg:hidden"
      aria-label="Toggle navigation menu"
      :aria-expanded="sidebarOpen"
      @click="emit('toggle-sidebar')"
    >
      <Menu class="size-5" aria-hidden="true" />
    </Button>

    <!-- Global search -->
    <div class="relative w-full max-w-md">
      <Search
        class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <Input type="search" placeholder="Search trips, jobs, trucks…" class="h-10 pl-9 pr-14" aria-label="Search" />
      <kbd
        class="pointer-events-none absolute right-3 top-1/2 flex h-5 -translate-y-1/2 items-center gap-0.5 rounded border bg-muted px-1.5 font-sans text-[11px] font-semibold text-muted-foreground"
        aria-hidden="true"
      >
        ⌘K
      </kbd>
    </div>

    <div class="ml-auto flex items-center gap-1.5">
      <Button variant="ghost" size="icon" aria-label="Refresh data" title="Refresh" @click="emit('refresh')">
        <RefreshCw class="size-[18px]" aria-hidden="true" />
      </Button>
      <Button variant="ghost" size="icon" class="relative" aria-label="Notifications" title="Notifications">
        <Bell class="size-[18px]" aria-hidden="true" />
        <span class="absolute right-2 top-2 size-2 rounded-full bg-red-500 ring-2 ring-card" aria-hidden="true" />
      </Button>
      <Avatar class="ml-1 size-10" aria-label="User: SR">
        <AvatarFallback>SR</AvatarFallback>
      </Avatar>
    </div>
  </header>
</template>
