import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { ChecklistResponse } from '../../api/types'
import { CameraPreview } from '../../components/CameraPreview'
import { useAppStore } from '../../store/appStore'
import { AutoDetectPanel } from './AutoDetectPanel'
import { ChecklistPanel } from './ChecklistPanel'
import { PracticeTools } from './PracticeTools'
import styles from './RecordingPage.module.css'

export function RecordingPage() {
  const status = useAppStore((s) => s.status)
  const streamSession = useAppStore((s) => s.streamSession)
  const setTab = useAppStore((s) => s.setTab)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null)

  const recording = Boolean(status?.is_recording)
  const autoOn = Boolean(status?.auto_detect_enabled)
  const label1 = status?.camera_labels?.camera1 || 'Face-On'
  const label2 = status?.camera_labels?.camera2 || 'Down-the-Line'

  const refreshChecklist = async () => {
    try {
      const data = await api.checklist()
      setChecklist(data)
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    void refreshChecklist()
    if (recording || status?.is_analyzing) return
    const id = setInterval(() => void refreshChecklist(), 2000)
    return () => clearInterval(id)
  }, [recording, status?.is_analyzing])

  // After stop+analyze, jump to Analysis when results appear
  useEffect(() => {
    if (status?.is_analyzing) setTab('analysis')
  }, [status?.is_analyzing, setTab])

  const toggleRecord = async () => {
    setBusy(true)
    setError(null)
    try {
      const result = recording ? await api.stopRecording() : await api.startRecording()
      if (result.error) {
        setError(result.error)
        if ('checklist' in result && result.checklist) setChecklist(result.checklist)
      } else if (!recording) {
        await refreshChecklist()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Recording failed')
    } finally {
      setBusy(false)
    }
  }

  const toggleAuto = async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await api.toggleAutoDetect()
      if (data.error) {
        setError(data.error)
        if (data.checklist) setChecklist(data.checklist)
      } else {
        await refreshChecklist()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Auto-detect failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className={styles.page}>
      <div className={`${styles.dual} ${autoOn ? styles.autoActive : ''}`}>
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
        <div className={styles.statusRow}>
          <span className={`${styles.dot} ${recording ? styles.dotLive : ''}`} />
          <div>
            <div className={styles.label}>
              {autoOn
                ? 'Auto-detect armed'
                : recording
                  ? 'Recording'
                  : 'Ready to record'}
            </div>
            <div className={styles.detail}>
              {status?.width || 1280}×{status?.height || 720} @ {status?.fps || 120}fps
              {' · '}
              Space to start/stop
            </div>
          </div>
          {recording && status?.recording_duration != null && (
            <span className={styles.duration}>
              {status.recording_duration.toFixed(1)}s
            </span>
          )}
        </div>

        <div className={styles.buttons}>
          {!autoOn && (
            <button
              type="button"
              className={recording ? styles.stop : styles.start}
              disabled={busy}
              onClick={() => void toggleRecord()}
            >
              {recording ? 'Stop recording' : 'Start recording'}
            </button>
          )}
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={autoOn}
              disabled={busy || recording}
              onChange={() => void toggleAuto()}
            />
            Auto detect
          </label>
        </div>

        <AutoDetectPanel enabled={autoOn} status={status?.auto_detect_status} />
        {error && <p className={styles.error}>{error}</p>}
      </div>

      <ChecklistPanel checklist={checklist} />
      <PracticeTools />
    </section>
  )
}
