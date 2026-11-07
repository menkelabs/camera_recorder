import { onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api/client'
import { useAppStore } from '../store/appStore'

/** Poll /api/status - faster while recording/analyzing, slower when idle. */
export function useStatusPoll() {
  const appStore = useAppStore()
  const busy = ref(false)
  let cancelled = false
  let wasAnalyzing = false
  let timer: ReturnType<typeof setTimeout> | undefined

  const tick = async () => {
    try {
      const data = await api.status()
      if (!cancelled) {
        const analyzing = Boolean(data.is_analyzing)
        busy.value = Boolean(data.is_recording || analyzing)
        appStore.setStatus(data)
        if (wasAnalyzing && !analyzing) appStore.bumpLibrary()
        wasAnalyzing = analyzing
      }
    } catch (err) {
      if (!cancelled) {
        appStore.setStatusError(err instanceof Error ? err.message : 'Status poll failed')
      }
    } finally {
      if (!cancelled) {
        timer = setTimeout(tick, busy.value ? 500 : 1500)
      }
    }
  }

  onMounted(() => {
    void tick()
  })

  onUnmounted(() => {
    cancelled = true
    if (timer) clearTimeout(timer)
  })
}
