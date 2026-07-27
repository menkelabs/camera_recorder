import { useState } from 'react'
import { api } from '../../api/client'
import { CameraPreview } from '../../components/CameraPreview'
import { useAppStore } from '../../store/appStore'
import styles from './RecordingPage.module.css'

export function RecordingPage() {
  const status = useAppStore((s) => s.status)
  const streamSession = useAppStore((s) => s.streamSession)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const recording = Boolean(status?.is_recording)
  const label1 = status?.camera_labels?.camera1 || 'Face-On'
  const label2 = status?.camera_labels?.camera2 || 'Down-the-Line'

  const toggleRecord = async () => {
    setBusy(true)
    setError(null)
    try {
      const result = recording ? await api.stopRecording() : await api.startRecording()
      if (result.error) setError(result.error)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recording failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className={styles.page}>
      <div className={styles.dual}>
        <CameraPreview
          cameraNum={1}
          active
          session={streamSession}
          recording={recording}
          label={`Camera 1 (${label1})`}
        />
        <CameraPreview
          cameraNum={2}
          active
          session={streamSession}
          recording={recording}
          label={`Camera 2 (${label2})`}
        />
      </div>
      <div className={styles.controls}>
        <button
          type="button"
          className={recording ? styles.stop : styles.start}
          disabled={busy}
          onClick={() => void toggleRecord()}
        >
          {recording ? 'Stop recording' : 'Start recording'}
        </button>
        {recording && status?.recording_duration != null && (
          <span className={styles.duration}>
            {status.recording_duration.toFixed(1)}s
          </span>
        )}
        {error && <p className={styles.error}>{error}</p>}
        <p className={styles.hint}>
          Live MJPEG continues while recording (v2). Hidden tabs release their feeds.
        </p>
      </div>
    </section>
  )
}
