<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Search, ChevronDown, LoaderCircle } from 'lucide-vue-next'

const props = withDefaults(defineProps<{ modelValue: string; options: string[]; placeholder?: string; loading?: boolean; disabled?: boolean }>(), { placeholder: 'Search…', loading: false, disabled: false })
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void; (event: 'search', value: string): void }>()
const open = ref(false); const query = ref(props.modelValue)
watch(() => props.modelValue, (value) => { if (!open.value) query.value = value })
const visible = computed(() => props.options.filter((item) => item.toLowerCase().includes(query.value.toLowerCase())).slice(0, 25))
function choose(value: string) { query.value = value; open.value = false; emit('update:modelValue', value) }
function search() { open.value = true; emit('search', query.value) }
</script>
<template>
  <div class="relative">
    <Search class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
    <input v-model="query" :disabled="disabled" :placeholder="placeholder" class="control pl-9 pr-9" role="combobox" :aria-expanded="open" @focus="search" @input="search" @keydown.esc="open = false" />
    <LoaderCircle v-if="loading" class="absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground" /><ChevronDown v-else class="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
    <div v-if="open && !disabled" class="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border bg-card p-1 shadow-lg" role="listbox">
      <button v-for="item in visible" :key="item" type="button" class="block w-full rounded-md px-3 py-2 text-left text-sm hover:bg-accent" @mousedown.prevent="choose(item)">{{ item }}</button>
      <p v-if="!loading && !visible.length" class="px-3 py-3 text-sm text-muted-foreground">No matching records.</p>
    </div>
  </div>
</template>
<style scoped>.control { @apply h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50; }</style>
