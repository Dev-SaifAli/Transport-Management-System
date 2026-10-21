<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'
import { computed, type HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold [&_svg]:size-3',
  {
    variants: {
      variant: {
        default: 'bg-[#0466C8]/10 text-[#023E7D] border border-[#0466C8]/25',
        // Preserve the base-only styling already used by Create Trip.
        secondary: '',
        blue: 'bg-[#0466C8]/10 text-[#0353A4] border border-[#0466C8]/25',
        deepsea: 'bg-[#023E7D]/10 text-[#023E7D] border border-[#023E7D]/25',
        amber: 'bg-amber-50 text-amber-900 border border-amber-200/70',
        green: 'bg-emerald-50 text-emerald-800 border border-emerald-200/70',
        red: 'bg-rose-50 text-rose-800 border border-rose-200/70',
        outline: 'border border-border/80 bg-card text-foreground shadow-xs',
        muted: 'bg-muted/70 text-muted-foreground border border-border/50',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

type BadgeVariants = VariantProps<typeof badgeVariants>

interface Props {
  variant?: BadgeVariants['variant']
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), { variant: 'default' })

const classes = computed(() => cn(badgeVariants({ variant: props.variant }), props.class))
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>
