import { customRef, ref, watch, type Ref } from 'vue'

/**
 * Creates a debounced ref that delays updating its value until after
 * the specified delay in milliseconds has elapsed since the last change.
 *
 * @param source Source ref to debounce, or initial value
 * @param delay Milliseconds to delay (default: 300ms)
 */
export function useDebounce<T>(source: Ref<T>, delay = 300): Readonly<Ref<T>> {
  const debounced = ref(source.value) as Ref<T>
  let timeout: ReturnType<typeof setTimeout> | undefined

  watch(
    source,
    (newVal) => {
      if (timeout) clearTimeout(timeout)
      timeout = setTimeout(() => {
        debounced.value = newVal
      }, delay)
    },
    { immediate: false }
  )

  return debounced
}

/**
 * Creates a debounced function that delays invoking `fn` until after
 * `delay` milliseconds have elapsed since the last time it was invoked.
 *
 * @param fn Function to debounce
 * @param delay Milliseconds to delay (default: 300ms)
 */
export function useDebouncedFn<T extends (...args: any[]) => any>(
  fn: T,
  delay = 300
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | undefined

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => {
      fn(...args)
    }, delay)
  }
}

/**
 * Standalone debounced ref initialized with a value (like refDebounced).
 */
export function refDebounced<T>(initialValue: T, delay = 300) {
  let value = initialValue
  let timeout: ReturnType<typeof setTimeout> | undefined

  return customRef((track, trigger) => ({
    get() {
      track()
      return value
    },
    set(newVal: T) {
      if (timeout) clearTimeout(timeout)
      timeout = setTimeout(() => {
        value = newVal
        trigger()
      }, delay)
    },
  }))
}

