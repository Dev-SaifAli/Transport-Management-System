<script setup lang="ts">
import { ExternalLink, RefreshCw, X } from 'lucide-vue-next'
import TomSelect from 'tom-select'
import 'tom-select/dist/css/tom-select.css'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDebouncedFn } from '@/composables/useDebounce'

export interface MasterOption {
  value: string
  text: string
  subtext?: string
}

interface Props {
  modelValue?: string | string[]
  options: MasterOption[]
  label?: string
  required?: boolean
  placeholder?: string
  doctype?: string // 'Customer' | 'Item' | 'Vehicle' | 'Driver' | 'Location' | etc.
  createUrl?: string
  allowCreate?: boolean
  multiple?: boolean
  maxOptions?: number
  disabled?: boolean
  loading?: boolean
  showRefresh?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  label: '',
  required: false,
  placeholder: 'Select...',
  doctype: 'Record',
  createUrl: '',
  allowCreate: true,
  multiple: false,
  maxOptions: 7,
  disabled: false,
  loading: false,
  showRefresh: true,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | string[]): void
  (e: 'change', value: string | string[]): void
  (e: 'refresh'): void
  (e: 'search', query: string): void
}>()

const selectEl = ref<HTMLSelectElement | null>(null)
let tomInstance: TomSelect | null = null
let isInternalChange = false
const currentQuery = ref('')
const isRefreshing = ref(false)

const debouncedEmitSearch = useDebouncedFn((query: string) => {
  emit('search', query)
}, 300)

function clearSelection() {
  if (tomInstance) {
    tomInstance.clear()
    tomInstance.setTextboxValue('')
  }
  currentQuery.value = ''
  emit('update:modelValue', props.multiple ? [] : '')
  emit('change', props.multiple ? [] : '')
}

function getCreateUrl(query: string = ''): string {
  if (props.createUrl) {
    if (props.createUrl.includes('{query}')) {
      return props.createUrl.replace('{query}', encodeURIComponent(query))
    }
    return query ? `${props.createUrl}?name=${encodeURIComponent(query)}` : props.createUrl
  }

  const dt = props.doctype.toLowerCase()
  if (dt === 'customer') {
    return query
      ? `/app/customer/new?customer_name=${encodeURIComponent(query)}`
      : '/app/customer/new'
  }
  if (dt === 'cargo types' || dt === 'cargo_types' || dt === 'material') {
    return query
      ? `/desk/cargo-types/new?cargo_name=${encodeURIComponent(query)}`
      : '/desk/cargo-types/new'
  }
  if (dt === 'item') {
    return query
      ? `/app/item/new?item_name=${encodeURIComponent(query)}`
      : '/app/item/new'
  }
  if (dt === 'vehicle' || dt === 'truck') {
    return '/app/vehicle/new'
  }
  if (dt === 'driver') {
    return '/app/driver/new'
  }
  return `/app/${dt}/new`
}

function openCreateInERPNext(query: string = '') {
  const url = getCreateUrl(query)
  window.open(url, '_blank')
}

function handleManualRefresh() {
  isRefreshing.value = true
  emit('refresh')
  setTimeout(() => {
    isRefreshing.value = false
  }, 800)
}

function onWindowFocus() {
  emit('refresh')
}

function attachFooterButton() {
  if (!tomInstance || !props.allowCreate) return
  const dropdown = tomInstance.dropdown
  if (!dropdown) return

  // Check if footer already exists
  let footer = dropdown.querySelector('.ts-pinned-create-footer') as HTMLElement | null
  if (!footer) {
    footer = document.createElement('div')
    footer.className = 'ts-pinned-create-footer border-t border-border/80 bg-muted/40 p-2 text-center'
    dropdown.appendChild(footer)
  }

  const query = currentQuery.value.trim()
  const labelText = query
    ? `+ Create "${query}" in ERPNext ${props.doctype} ↗`
    : `+ Create new ${props.doctype} in ERPNext ↗`

  footer.innerHTML = `
    <button
      type="button"
      class="inline-flex w-full items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary/10 hover:underline cursor-pointer"
    >
      <span>${labelText}</span>
    </button>
  `

  const btn = footer.querySelector('button')
  if (btn) {
    btn.onmousedown = (e) => {
      e.preventDefault()
      e.stopPropagation()
      openCreateInERPNext(currentQuery.value.trim())
    }
  }
}

function initTomSelect() {
  if (!selectEl.value) return

  if (tomInstance) {
    tomInstance.destroy()
    tomInstance = null
  }

  tomInstance = new TomSelect(selectEl.value, {
    valueField: 'value',
    labelField: 'text',
    searchField: ['text', 'subtext'],
    maxOptions: props.maxOptions || 7,
    maxItems: props.multiple ? null : 1,
    placeholder: props.placeholder,
    allowEmptyOption: true,
    closeAfterSelect: !props.multiple,
    plugins: props.multiple ? ['remove_button'] : [],
    options: props.options,
    items: Array.isArray(props.modelValue)
      ? props.modelValue
      : props.modelValue
        ? [props.modelValue]
        : [],
    render: {
      option: (data: any, escape: any) => {
        return `<div class="py-2 px-3 flex items-center justify-between text-sm hover:bg-muted/50 cursor-pointer">
          <span class="font-medium text-foreground">${escape(data.text)}</span>
          ${data.subtext ? `<span class="text-xs text-muted-foreground font-mono">${escape(data.subtext)}</span>` : ''}
        </div>`
      },
      item: (data: any, escape: any) => {
        return `<div class="inline-flex items-center gap-1.5 bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-md text-xs font-semibold">
          <span>${escape(data.text)}</span>
        </div>`
      },
      no_results: (data: any, escape: any) => {
        const query = escape(data.input || '')
        if (props.allowCreate) {
          return `<div class="p-3 text-center">
            <p class="text-xs text-muted-foreground mb-2">No matching ${escape(props.doctype)} found${query ? ` for "${query}"` : ''}.</p>
            <button
              type="button"
              id="ts-create-no-results-btn"
              class="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground shadow-xs transition-all hover:bg-primary/90 cursor-pointer"
            >
              <span>+ Create ${query ? `"${query}"` : `new ${escape(props.doctype)}`} in ERPNext</span>
              <svg class="size-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            </button>
          </div>`
        }
        return `<div class="p-3 text-center text-xs text-muted-foreground">No matching records found.</div>`
      },
    },
    onType: (str: string) => {
      currentQuery.value = str
      debouncedEmitSearch(str)
      nextTick(() => {
        attachFooterButton()
        const noResultsBtn = document.getElementById('ts-create-no-results-btn')
        if (noResultsBtn) {
          noResultsBtn.onmousedown = (e) => {
            e.preventDefault()
            e.stopPropagation()
            openCreateInERPNext(currentQuery.value.trim())
          }
        }
      })
    },
    onDropdownOpen: () => {
      nextTick(() => {
        attachFooterButton()
        const noResultsBtn = document.getElementById('ts-create-no-results-btn')
        if (noResultsBtn) {
          noResultsBtn.onmousedown = (e) => {
            e.preventDefault()
            e.stopPropagation()
            openCreateInERPNext(currentQuery.value.trim())
          }
        }
      })
    },
    onChange: (val: any) => {
      isInternalChange = true
      emit('update:modelValue', val)
      emit('change', val)
      setTimeout(() => {
        isInternalChange = false
      }, 0)
    },
  })

  if (props.disabled && tomInstance) {
    tomInstance.disable()
  }
}

onMounted(async () => {
  await nextTick()
  initTomSelect()
  window.addEventListener('focus', onWindowFocus)
})

onBeforeUnmount(() => {
  window.removeEventListener('focus', onWindowFocus)
  if (tomInstance) {
    tomInstance.destroy()
    tomInstance = null
  }
})

watch(
  () => props.modelValue,
  (newVal) => {
    if (isInternalChange || !tomInstance) return
    if (props.multiple && Array.isArray(newVal)) {
      tomInstance.setValue(newVal, true)
    } else if (!props.multiple && typeof newVal === 'string') {
      tomInstance.setValue(newVal, true)
    }
  },
  { deep: true },
)

watch(
  () => props.options,
  (newOpts) => {
    if (!tomInstance) return
    tomInstance.clearOptions()
    tomInstance.addOptions(newOpts)
    const currentVal = Array.isArray(props.modelValue) ? props.modelValue : props.modelValue ? [props.modelValue] : []
    if (currentVal.length > 0) {
      tomInstance.setValue(currentVal, true)
    }
    tomInstance.refreshOptions(false)
    nextTick(attachFooterButton)
  },
  { deep: true },
)

watch(
  () => props.disabled,
  (val) => {
    if (!tomInstance) return
    if (val) tomInstance.disable()
    else tomInstance.enable()
  },
)
</script>

<template>
  <div class="master-select-component w-full">
    <div v-if="label" class="mb-1.5 flex items-center justify-between">
      <label class="block text-xs font-semibold text-foreground">
        {{ label }}
        <span v-if="required" class="ml-0.5 text-destructive">*</span>
      </label>
      <div class="flex items-center gap-1.5">
        <button
          v-if="showRefresh"
          type="button"
          class="rounded p-1 text-muted-foreground/80 transition-colors hover:bg-muted hover:text-foreground cursor-pointer"
          :title="`Refresh ${doctype} list from ERPNext`"
          :aria-label="`Refresh ${doctype} list`"
          @click="handleManualRefresh"
        >
          <RefreshCw class="size-3" :class="{ 'animate-spin': isRefreshing || loading }" />
        </button>
        <button
          v-if="allowCreate"
          type="button"
          class="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline cursor-pointer"
          :title="`Create new ${doctype} in ERPNext`"
          @click="openCreateInERPNext()"
        >
          <span>ERPNext</span>
          <ExternalLink class="size-2.5" />
        </button>
      </div>
    </div>

    <div class="master-select-wrapper relative w-full" :class="{ 'is-disabled': disabled }">
      <select ref="selectEl" :multiple="multiple" class="w-full"></select>

      <!-- Inline Loading Spinner -->
      <div
        v-if="loading"
        class="pointer-events-none absolute right-8 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-[11px] font-medium text-slate-500 bg-white/90 px-1.5 py-0.5 rounded shadow-2xs z-10"
      >
        <span class="size-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></span>
        <span>Loading…</span>
      </div>

      <!-- Clear Button (✕) -->
      <button
        v-if="!disabled && ((Array.isArray(modelValue) ? modelValue.length > 0 : Boolean(modelValue)) || currentQuery)"
        type="button"
        class="absolute right-7 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 rounded-full cursor-pointer z-10 transition-colors"
        title="Clear selection"
        @click.stop="clearSelection"
      >
        <X class="size-3.5" />
      </button>
    </div>
  </div>
</template>

<style>
.master-select-wrapper .ts-wrapper {
  min-height: 40px;
}
.master-select-wrapper .ts-control {
  min-height: 40px;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  background: #ffffff;
  padding: 0.45rem 0.75rem;
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.25rem;
}
.master-select-wrapper .ts-control:hover {
  border-color: #94a3b8;
}
.master-select-wrapper .ts-control:focus-within {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}
.master-select-wrapper.is-disabled .ts-control,
.master-select-wrapper .ts-control.disabled {
  background: rgba(241, 245, 249, 0.8) !important;
  border-color: #e2e8f0 !important;
  color: #64748b !important;
  cursor: not-allowed !important;
}
.master-select-wrapper .ts-control > input {
  min-width: 0;
  padding: 0;
  color: #0f172a;
}
.master-select-wrapper .ts-control > input::placeholder {
  color: #94a3b8;
  opacity: 1;
}
.master-select-wrapper .ts-dropdown {
  z-index: 50;
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  background: #ffffff;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
}
.master-select-wrapper .ts-dropdown .option {
  padding: 0.55rem 0.75rem;
  font-size: 0.875rem;
  border-bottom: 1px solid #f1f5f9;
}
.master-select-wrapper .ts-dropdown .option:last-child {
  border-bottom: none;
}
.master-select-wrapper .ts-dropdown .active {
  background: #f1f5f9;
  color: #0f172a;
}
</style>

