<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import TomSelect from 'tom-select'
import 'tom-select/dist/css/tom-select.css'

interface OptionItem {
  value: string
  text: string
  subtext?: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string | string[]
    options: OptionItem[]
    placeholder?: string
    multiple?: boolean
    maxItems?: number
    allowEmptyOption?: boolean
    disabled?: boolean
  }>(),
  {
    placeholder: 'Select...',
    multiple: false,
    allowEmptyOption: false,
    disabled: false,
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | string[]): void
  (e: 'change', value: string | string[]): void
}>()

const selectEl = ref<HTMLSelectElement | null>(null)
let tomInstance: TomSelect | null = null
let isInternalChange = false

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
    maxItems: props.multiple ? (props.maxItems || null) : 1,
    placeholder: props.placeholder,
    allowEmptyOption: props.allowEmptyOption,
    plugins: props.multiple ? ['remove_button'] : [],
    options: props.options,
    items: Array.isArray(props.modelValue) ? props.modelValue : props.modelValue ? [props.modelValue] : [],
    render: {
      option: (data: any, escape: any) => {
        return `<div class="py-1.5 px-2.5 flex items-center justify-between text-sm hover:bg-slate-50 cursor-pointer">
          <span class="font-medium text-slate-800">${escape(data.text)}</span>
          ${data.subtext ? `<span class="text-xs text-slate-400 font-mono">${escape(data.subtext)}</span>` : ''}
        </div>`
      },
      item: (data: any, escape: any) => {
        return `<div class="inline-flex items-center gap-1.5 bg-primary/10 text-primary border border-primary/20 px-2.5 py-0.5 rounded-md text-xs font-medium">
          <span>${escape(data.text)}</span>
        </div>`
      },
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
})

onBeforeUnmount(() => {
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
  { deep: true }
)

watch(
  () => props.options,
  (newOpts) => {
    if (!tomInstance) return
    tomInstance.clearOptions()
    tomInstance.addOptions(newOpts)
    tomInstance.refreshOptions(false)
  },
  { deep: true }
)

watch(
  () => props.disabled,
  (val) => {
    if (!tomInstance) return
    if (val) tomInstance.disable()
    else tomInstance.enable()
  }
)
</script>

<template>
  <div class="tom-select-wrapper w-full">
    <select ref="selectEl" :multiple="multiple" class="w-full"></select>
  </div>
</template>

<style scoped>
.tom-select-wrapper .ts-wrapper {
  min-height: 40px;
}
.tom-select-wrapper .ts-control {
  min-height: 40px;
  border: 1px solid hsl(var(--input));
  border-radius: 0.5rem;
  background: hsl(var(--background));
  padding: 0.55rem 0.75rem;
  box-shadow: none;
}
.tom-select-wrapper .ts-control > input {
  min-width: 0;
  padding: 0;
  color: hsl(var(--foreground));
}
.tom-select-wrapper .ts-control > input::placeholder {
  color: hsl(var(--muted-foreground));
  opacity: 1;
}
.tom-select-wrapper .ts-dropdown {
  z-index: 50;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  background: hsl(var(--card));
  box-shadow: 0 10px 30px rgb(15 23 42 / 12%);
}
.tom-select-wrapper .ts-dropdown .option {
  padding: 0.65rem 0.75rem;
  font-size: 0.875rem;
}
.tom-select-wrapper .ts-dropdown .active {
  background: hsl(var(--accent));
  color: hsl(var(--accent-foreground));
}
</style>