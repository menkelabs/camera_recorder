import { onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

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
export function useMetronome(bpm: Ref<number>, enabled: Ref<boolean>) {
  const beatAccent = ref(false)
  const pulse = ref(0)
  let ctx: AudioCtx | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let beat = 0

  const stop = () => {
    if (timer) clearTimeout(timer)
    timer = null
  }

  const start = () => {
    stop()
    beat = 0
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AC) return
    ctx ||= new AC()
    if (ctx.state === 'suspended') void ctx.resume()

    const tick = () => {
      if (!ctx) return
      const accent = beat % 4 === 0
      createClick(ctx, accent)
      beatAccent.value = accent
      pulse.value += 1
      beat += 1
      timer = setTimeout(tick, Math.round(60000 / Math.max(40, bpm.value)))
    }

    tick()
  }

  watch(
    [enabled, bpm],
    () => {
      if (enabled.value) start()
      else stop()
    },
    { immediate: true },
  )

  onUnmounted(stop)

  return { beatAccent, pulse }
}
