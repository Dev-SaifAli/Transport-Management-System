<script setup lang="ts">
import { computed, ref } from 'vue'
import { MapPin, Search, X } from 'lucide-vue-next'
interface Location { name: string; usage: string }
const props = withDefaults(defineProps<{ modelValue: string[]; options: Location[]; placeholder?: string; disabled?: boolean }>(), { placeholder: 'Search locations…', disabled: false })
const emit = defineEmits<{ (event: 'update:modelValue', value: string[]): void; (event: 'search', value: string): void }>()
const query = ref(''); const open = ref(false)
const visible = computed(() => props.options.filter((item) => !props.modelValue.includes(item.name) && item.name.toLowerCase().includes(query.value.toLowerCase())).slice(0, 25))
function add(name: string) { emit('update:modelValue', [...props.modelValue, name]); query.value = ''; open.value = false }
function remove(name: string) { emit('update:modelValue', props.modelValue.filter((item) => item !== name)) }
function search() { open.value = true; emit('search', query.value) }
</script>
<template>
  <div class="relative"><div class="flex min-h-10 flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1.5 focus-within:ring-2 focus-within:ring-ring" :class="{ 'opacity-50': disabled }"><span v-for="item in modelValue" :key="item" class="inline-flex items-center gap-1 rounded-md bg-accent px-2 py-1 text-xs font-semibold text-accent-foreground">{{ item }}<button type="button" :disabled="disabled" aria-label="Remove location" @click="remove(item)"><X class="size-3" /></button></span><Search class="ml-1 size-4 shrink-0 text-muted-foreground" /><input v-model="query" :disabled="disabled" :placeholder="modelValue.length ? '' : placeholder" class="min-w-[160px] flex-1 bg-transparent px-1 text-sm outline-none" role="combobox" :aria-expanded="open" @focus="search" @input="search" @keydown.esc="open = false" /></div><div v-if="open && !disabled" class="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border bg-card p-1 shadow-lg" role="listbox"><button v-for="item in visible" :key="item.name" type="button" class="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-accent" @mousedown.prevent="add(item.name)"><MapPin class="size-4 text-muted-foreground" />{{ item.name }}</button><p v-if="!visible.length" class="px-3 py-3 text-sm text-muted-foreground">No matching locations.</p></div></div>
</template>
