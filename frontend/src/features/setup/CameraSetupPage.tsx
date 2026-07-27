import { useState } from 'react'
import { api } from '../../api/client'
import { CameraPreview } from '../../components/CameraPreview'
import { PropertySliders } from '../../components/PropertySliders'
import { useAppStore } from '../../store/appStore'
import styles from './CameraSetupPage.module.css'

interface Props {
  cameraNum: 1 | 2
}

export function CameraSetupPage({ cameraNum }: Props) {
  const streamSession = useAppStore((s) => s.streamSession)
  const bumpStreamSession = useAppStore((s) => s.bumpStreamSession)
  const status = useAppStore((s) => s.status)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const label =
    cameraNum === 1
      ? status?.camera_labels?.camera1 || 'Face-On'
      : status?.camera_labels?.camera2 || 'Down-the-Line'

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setMessage(null)
    try {
      await fn()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className={styles.page}>
      <div className={styles.layout}>
        <CameraPreview
          cameraNum={cameraNum}
          active
          session={streamSession}
          label={`Camera ${cameraNum} (${label}) · index ${
            cameraNum === 1 ? status?.camera1_id ?? '?' : status?.camera2_id ?? '?'
          }`}
        />
        <div className={styles.controls}>
          <h3>Properties</h3>
          <PropertySliders cameraNum={cameraNum} active />
          <div className={styles.actions}>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  const res = await api.saveSettings()
                  setMessage(
                    res.success
                      ? `Saved ${res.filename}`
                      : res.error || 'Save failed',
                  )
                })
              }
            >
              Save settings
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api.resetCamera(cameraNum)
                  setMessage(`Camera ${cameraNum} reset to defaults`)
                })
              }
            >
              Reset defaults
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api.reinitCameras()
                  bumpStreamSession()
                  setMessage('Cameras re-initialized')
                })
              }
            >
              Reinit
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  const res = await api.detectCameras()
                  bumpStreamSession()
                  setMessage(
                    `Found indices [${res.available_indices.join(', ')}] · ` +
                      `using ${res.camera1_id}/${res.camera2_id}`,
                  )
                })
              }
            >
              Detect
            </button>
          </div>
          {message && <p className={styles.message}>{message}</p>}
        </div>
      </div>
    </section>
  )
}
