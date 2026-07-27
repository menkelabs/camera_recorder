import type { AutoDetectStatus } from '../../api/types'
import styles from './AutoDetectPanel.module.css'

interface Props {
  enabled: boolean
  status?: AutoDetectStatus
}

export function AutoDetectPanel({ enabled, status }: Props) {
  if (!enabled) return null

  const state = (status?.state || 'idle').replace(/_/g, ' ')
  const delta = status?.delta
  const threshold = status?.motion_threshold || 15
  const pct =
    delta != null ? Math.min(100, (Number(delta) / (threshold * 2)) * 100) : 0

  let badgeClass = styles.idle
  if (status?.state === 'motion_detected') badgeClass = styles.motion
  else if (status?.state === 'recording') badgeClass = styles.recording
  else if (status?.state === 'cooldown') badgeClass = styles.cooldown

  return (
    <div className={styles.panel}>
      <div className={styles.row}>
        <span className={`${styles.badge} ${badgeClass}`}>{state}</span>
        <span className={styles.info}>Watching for swing…</span>
      </div>
      <div className={styles.gauge}>
        <span className={styles.gaugeLabel}>Shoulder turn Δ</span>
        <div className={styles.barBg}>
          <div className={styles.barFill} style={{ width: `${pct}%` }} />
        </div>
        <span className={styles.gaugeValue}>
          {delta != null ? `${Number(delta).toFixed(1)}°` : '—'}
        </span>
      </div>
    </div>
  )
}
