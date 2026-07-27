import { useEffect, useState } from 'react'
import styles from './CameraPreview.module.css'

export interface CameraPreviewProps {
  cameraNum: 1 | 2
  /** When false, MJPEG src is cleared so the browser drops the stream. */
  active: boolean
  /** Bump after reinit/detect to force reconnect. */
  session?: number
  label?: string
  recording?: boolean
  className?: string
}

/**
 * MJPEG preview that only connects while `active` is true.
 * Clearing `src` on hide/unmount pauses hidden feeds (v2 must-hit).
 */
export function CameraPreview({
  cameraNum,
  active,
  session = 0,
  label,
  recording = false,
  className,
}: CameraPreviewProps) {
  const [src, setSrc] = useState('')

  useEffect(() => {
    if (!active) {
      setSrc('')
      return
    }
    setSrc(`/video_feed/${cameraNum}?s=${session}`)
    return () => setSrc('')
  }, [active, cameraNum, session])

  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) setSrc('')
      else if (active) setSrc(`/video_feed/${cameraNum}?s=${session}&r=${Date.now()}`)
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [active, cameraNum, session])

  return (
    <div className={`${styles.card} ${className || ''}`}>
      <div className={styles.frame}>
        {src ? (
          <img src={src} alt={label || `Camera ${cameraNum}`} />
        ) : (
          <div className={styles.placeholder}>Feed paused</div>
        )}
        {recording && active && <span className={styles.recBadge}>REC</span>}
      </div>
      {label && <div className={styles.label}>{label}</div>}
    </div>
  )
}
