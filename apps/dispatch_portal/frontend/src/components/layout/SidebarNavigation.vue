<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { cn } from '@/lib/utils'

import { navigationSections } from './navigation'

interface Props {
  collapsed: boolean
}

defineProps<Props>()

const emit = defineEmits<{ (e: 'navigate'): void }>()
</script>

<template>
  <nav aria-label="Primary" class="flex-1 space-y-6 overflow-y-auto px-3 py-4">
    <div v-for="section in navigationSections" :key="section.label">
      <p
        v-if="!collapsed"
        class="mb-1.5 px-3 text-[11px] font-bold uppercase tracking-widest text-muted-foreground/70"
      >
        {{ section.label }}
      </p>
      <ul class="space-y-1">
        <li v-for="item in section.items" :key="item.to">
          <RouterLink
            :to="item.to"
            :title="collapsed ? item.title : undefined"
            :aria-label="item.title"
            :aria-current="$route.path === item.to ? 'page' : undefined"
            class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold text-foreground/80 transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :class="cn({ 'justify-center px-0 py-2.5': collapsed })"
            active-class="!bg-primary !text-primary-foreground shadow-sm hover:!bg-primary"
            @click="emit('navigate')"
          >
            <component :is="item.icon" class="size-[18px] shrink-0" aria-hidden="true" />
            <span v-if="!collapsed" class="truncate">{{ item.title }}</span>
          </RouterLink>
        </li>
      </ul>
    </div>
  </nav>
</template>
