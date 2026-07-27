import { useAppStore } from '../store/appStore'
import styles from './AppHeader.module.css'

export function AppHeader() {
  const status = useAppStore((s) => s.status)
  const statusError = useAppStore((s) => s.statusError)

  const recording = status?.is_recording
  const analyzing = status?.is_analyzing
  const cams = status?.cameras_available

  return (
    <header className={styles.header}>
      <div>
        <p className={styles.brand}>SwingLab</p>
        <h1>Camera Setup &amp; Recording</h1>
      </div>
      <div className={styles.badges}>
        <span className={`${styles.badge} ${cams ? styles.ok : styles.warn}`}>
          {cams ? 'Cameras ready' : 'Cameras offline'}
        </span>
        {recording && <span className={`${styles.badge} ${styles.rec}`}>Recording</span>}
        {analyzing && <span className={`${styles.badge} ${styles.info}`}>Analyzing</span>}
        {status?.fps != null && (
          <span className={styles.badge}>Target {status.fps} fps</span>
        )}
      </div>
      {(status?.status_message || statusError) && (
        <div className={styles.message} role="status">
          {statusError || status?.status_message}
        </div>
      )}
    </header>
  )
}
