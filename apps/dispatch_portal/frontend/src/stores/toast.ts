import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToastMessage {
  text: string
  type: 'success' | 'error' | 'info'
}

export const useToastStore = defineStore('toast', () => {
  const toastMessage = ref<ToastMessage | null>(null)
  const timeoutId = ref<ReturnType<typeof setTimeout> | null>(null)

  function showToast(text: string, type: ToastMessage['type'] = 'info', duration = 3000) {
    if (timeoutId.value) {
      globalThis.clearTimeout(timeoutId.value)
    }
    toastMessage.value = { text, type }
    timeoutId.value = globalThis.setTimeout(() => {
      toastMessage.value = null
    }, duration)
  }

  function success(text: string, duration = 3000) {
    showToast(text, 'success', duration)
  }

  function error(text: string, duration = 5000) {
    showToast(text, 'error', duration)
  }

  function info(text: string, duration = 3000) {
    showToast(text, 'info', duration)
  }

  return {
    toastMessage,
    showToast,
    success,
    error,
    info,
  }
})