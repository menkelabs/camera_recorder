import { useEffect, useRef } from 'react'
import { api } from '../api/client'
import { useAppStore } from '../store/appStore'

/** Poll /api/status — faster while recording/analyzing, slower when idle. */
export function useStatusPoll() {
  const setStatus = useAppStore((s) => s.setStatus)
  const setStatusError = useAppStore((s) => s.setStatusError)
  const busyRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    const tick = async () => {
      try {
        const data = await api.status()
        if (!cancelled) {
          busyRef.current = Boolean(data.is_recording || data.is_analyzing)
          setStatus(data)
        }
      } catch (err) {
        if (!cancelled) {
          setStatusError(err instanceof Error ? err.message : 'Status poll failed')
        }
      } finally {
        if (!cancelled) {
          timer = setTimeout(tick, busyRef.current ? 500 : 1500)
        }
      }
    }

    tick()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [setStatus, setStatusError])
}
