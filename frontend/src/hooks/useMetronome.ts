import { useCallback, useEffect, useRef, useState } from 'react'

type AudioCtx = AudioContext

function createClick(ctx: AudioCtx, accent: boolean) {
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.frequency.value = accent ? 880 : 660
  gain.gain.value = accent ? 0.18 : 0.1
  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.start()
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.06)
  osc.stop(ctx.currentTime + 0.07)
}

/** Client-side 3:1 tempo metronome (accent every 4th beat). */
export function useMetronome(bpm: number, enabled: boolean) {
  const [beatAccent, setBeatAccent] = useState(false)
  const [pulse, setPulse] = useState(0)
  const ctxRef = useRef<AudioCtx | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const beatRef = useRef(0)
  const bpmRef = useRef(bpm)
  bpmRef.current = bpm

  const stop = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const start = useCallback(() => {
    stop()
    beatRef.current = 0
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AC) return
    if (!ctxRef.current) ctxRef.current = new AC()
    const ctx = ctxRef.current
    if (ctx.state === 'suspended') void ctx.resume()

    const tick = () => {
      const accent = beatRef.current % 4 === 0
      createClick(ctx, accent)
      setBeatAccent(accent)
      setPulse((p) => p + 1)
      beatRef.current += 1
      timerRef.current = setTimeout(tick, Math.round(60000 / Math.max(40, bpmRef.current)))
    }
    tick()
  }, [stop])

  useEffect(() => {
    if (enabled) start()
    else stop()
    return stop
  }, [enabled, start, stop])

  // Restart cadence when BPM changes while running
  useEffect(() => {
    if (enabled) start()
  }, [bpm, enabled, start])

  return { beatAccent, pulse }
}
