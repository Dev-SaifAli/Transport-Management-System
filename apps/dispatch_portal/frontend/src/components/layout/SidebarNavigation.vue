<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { navigationSections } from './navigation'

interface Props {
  collapsed: boolean
}

defineProps<Props>()

const emit = defineEmits<{ (e: 'navigate'): void }>()
</script>

<template>
  <nav aria-label="Primary" class="space-y-6 px-2.5 py-4">
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
            class="group relative flex items-center rounded-xl text-sm font-medium text-muted-foreground transition-all hover:bg-card/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            :class="collapsed ? 'size-11 mx-auto justify-center' : 'w-full gap-3 px-3 py-2.5'"
            active-class="!bg-card !text-foreground !font-semibold shadow-2xs border border-border/80"
            @click="emit('navigate')"
          >
            <!-- Minimal Deep Sea Blue active indicator -->
            <span
              v-if="$route.path === item.to && !collapsed"
              class="absolute left-1 top-2.5 bottom-2.5 w-1 rounded-full bg-[#0466C8]"
              aria-hidden="true"
            />
            <component
              :is="item.icon"
              class="size-[18px] shrink-0 transition-colors"
              :class="$route.path === item.to ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground'"
              aria-hidden="true"
            />
            <span v-if="!collapsed" class="truncate">{{ item.title }}</span>
            <span
              v-if="$route.path === item.to && collapsed"
              class="absolute bottom-1.5 size-1.5 rounded-full bg-[#0466C8]"
              aria-hidden="true"
            />
          </RouterLink>
        </li>
      </ul>
    </div>
  </nav>
</template>
