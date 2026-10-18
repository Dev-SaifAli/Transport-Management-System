<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import EmptyState from '@/components/shared/EmptyState.vue'
import PageContainer from '@/components/shared/PageContainer.vue'
import PageHeader from '@/components/shared/PageHeader.vue'

const route = useRoute()

const title = computed(() => (route.meta.title as string | undefined) ?? 'Module')
</script>

<template>
  <PageContainer>
    <PageHeader :title="title" />
    <div class="rounded-2xl border bg-card shadow-sm">
      <EmptyState
        title="Screen design pending"
        :description="`The ${title} screen will be implemented once its design is approved. This placeholder exists so navigation is complete and honest.`"
      />
    </div>
  </PageContainer>
</template>
