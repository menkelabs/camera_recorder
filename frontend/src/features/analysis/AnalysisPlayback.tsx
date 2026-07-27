import { useEffect, useMemo, useRef, useState } from 'react'
import { analysisFrameUrl, api } from '../../api/client'
import { PlaybackSequencer, playIntervalMs } from './playbackSequencer'
import styles from './AnalysisPlayback.module.css'

const SPEEDS = [0.25, 0.5, 1, 2, 4]

interface Props {
  maxFrames: number
  initialIndex?: number
  onResults?: (data: unknown) => void
}

export function AnalysisPlayback({ maxFrames, initialIndex = 0, onResults }: Props) {
  const [index, setIndex] = useState(initialIndex)
  const [playing, setPlaying] = useState(false)
  const [speedIdx, setSpeedIdx] = useState(2)
  const [bust, setBust] = useState(0)
  const seqRef = useRef<PlaybackSequencer | null>(null)

  const speed = SPEEDS[speedIdx]

  useEffect(() => {
    const seq = new PlaybackSequencer(async (i) => {
      const data = await api.setAnalysisFrame(i)
      onResults?.(data)
      setBust((b) => b + 1)
    }, setIndex)
    seqRef.current = seq
    return () => seq.dispose()
  }, [onResults])

  useEffect(() => {
    if (!playing || maxFrames <= 1) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    const tick = () => {
      if (cancelled) return
      const next = index + 1
      if (next >= maxFrames) {
        setPlaying(false)
        return
      }
      seqRef.current?.request(next)
      timer = setTimeout(tick, playIntervalMs(speed))
    }

    timer = setTimeout(tick, playIntervalMs(speed))
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [playing, speed, maxFrames, index])

  const urls = useMemo(
    () => ({
      cam1: analysisFrameUrl(1, index, bust),
      cam2: analysisFrameUrl(2, index, bust),
    }),
    [index, bust],
  )

  if (maxFrames <= 0) {
    return <div className={styles.empty}>No annotated frames yet — record and analyze a swing.</div>
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.dual}>
        <img src={urls.cam1} alt="Camera 1 analysis" />
        <img src={urls.cam2} alt="Camera 2 analysis" />
      </div>
      <div className={styles.controls}>
        <button type="button" onClick={() => setPlaying((p) => !p)}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <button
          type="button"
          onClick={() => setSpeedIdx((i) => (i + 1) % SPEEDS.length)}
        >
          {speed}x
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(0, maxFrames - 1)}
          value={index}
          onChange={(e) => {
            setPlaying(false)
            seqRef.current?.request(Number(e.target.value))
          }}
        />
        <span className={styles.meta}>
          {index + 1} / {maxFrames}
        </span>
      </div>
    </div>
  )
}
