import { ref, watch, type Ref } from 'vue'

/**
 * Smoothly animates a number from its current value to the target value.
 * @param target Ref or getter of the target number
 * @param duration Duration of animation in ms (default: 800ms)
 */
export function useAnimatedNumber(target: Ref<number> | (() => number), duration: number = 800) {
  const current = ref(typeof target === 'function' ? target() : target.value)
  let animationFrameId: number | null = null

  function animate(startVal: number, endVal: number) {
    if (startVal === endVal) {
      current.value = endVal
      return
    }

    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
    }

    const startTime = performance.now()

    function step(now: number) {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)

      // Ease out cubic: 1 - pow(1 - progress, 3)
      const easeProgress = 1 - Math.pow(1 - progress, 3)
      current.value = Math.round(startVal + (endVal - startVal) * easeProgress)

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step)
      } else {
        current.value = endVal
        animationFrameId = null
      }
    }

    animationFrameId = requestAnimationFrame(step)
  }

  watch(
    () => (typeof target === 'function' ? target() : target.value),
    (newVal, oldVal) => {
      animate(typeof oldVal === 'number' ? oldVal : 0, newVal)
    },
    { immediate: true },
  )

  return current
}

