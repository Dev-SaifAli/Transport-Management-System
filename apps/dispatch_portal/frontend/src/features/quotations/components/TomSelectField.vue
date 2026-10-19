<script setup lang="ts">
import TomSelect from 'tom-select'
import 'tom-select/dist/css/tom-select.css'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type Option = string | { value: string; text: string }
const props = withDefaults(defineProps<{ modelValue: string; options: Option[]; placeholder?: string; loading?: boolean; disabled?: boolean; allowCreate?: boolean }>(), { placeholder: 'Search…', loading: false, disabled: false, allowCreate: false })
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void; (event: 'search', value: string): void; (event: 'create-new', value: string): void }>()
const selectElement = ref<HTMLSelectElement | null>(null); const query = ref(''); let control: TomSelect | undefined

function optionValues() { return props.options.map((option) => typeof option === 'string' ? { value: option, text: option } : option) }
function syncOptions() { if (!control) return; const selected = props.modelValue; control.clearOptions(); control.addOptions(optionValues()); if (selected && !optionValues().some((option) => option.value === selected)) control.addOption({ value: selected, text: selected }); control.setValue(selected, true); control.refreshOptions(false) }
function createNew() { emit('create-new', query.value.trim()) }
onMounted(async () => { await nextTick(); if (!selectElement.value) return; control = new TomSelect(selectElement.value, { options: optionValues(), valueField: 'value', labelField: 'text', searchField: ['text'], maxOptions: 50, closeAfterSelect: true, hideSelected: true, preload: true, placeholder: props.placeholder, onChange: (value: string) => emit('update:modelValue', value), onDropdownOpen: () => emit('search', query.value), onType: (value: string) => { query.value = value; emit('search', value) }, render: { no_results: (data: { input: string }) => `<div class="no-results">No matching records${props.allowCreate && data.input ? '.' : ''}</div>` } }); syncOptions() })
watch(() => props.options, syncOptions, { deep: true }); watch(() => props.modelValue, (value) => { if (control && control.getValue() !== value) control.setValue(value, true) }); watch(() => props.disabled, (value) => { if (value) control?.disable(); else control?.enable() })
onBeforeUnmount(() => { control?.destroy(); control = undefined })
</script>

<template>
  <div class="tom-select-field"><select ref="selectElement" :disabled="disabled"><option value="" /></select><span v-if="loading" class="loading-label">Loading…</span><button v-if="allowCreate && !disabled" type="button" class="create-link" @mousedown.prevent="createNew">+ Create new customer in ERPNext</button></div>
</template>

<style>
.tom-select-field { position: relative; }
.tom-select-field .ts-wrapper { min-height: 40px; }
.tom-select-field .ts-control { min-height: 40px; border: 1px solid hsl(var(--input)); border-radius: .5rem; background: hsl(var(--background)); padding: .55rem .75rem; box-shadow: none; }
.tom-select-field .ts-control > input { min-width: 0; padding: 0; color: hsl(var(--foreground)); }
.tom-select-field .ts-control > input::placeholder { color: hsl(var(--muted-foreground)); opacity: 1; }
.tom-select-field .ts-dropdown { z-index: 50; overflow: hidden; border: 1px solid hsl(var(--border)); border-radius: .5rem; background: hsl(var(--card)); box-shadow: 0 10px 30px rgb(15 23 42 / 12%); }
.tom-select-field .ts-dropdown .option { padding: .65rem .75rem; font-size: .875rem; }
.tom-select-field .ts-dropdown .active { background: hsl(var(--accent)); color: hsl(var(--accent-foreground)); }
.tom-select-field .loading-label { position: absolute; right: 2.25rem; top: .7rem; color: hsl(var(--muted-foreground)); font-size: .75rem; pointer-events: none; }
.tom-select-field .create-link { margin-top: .35rem; color: hsl(var(--primary)); font-size: .75rem; font-weight: 600; }
</style>
