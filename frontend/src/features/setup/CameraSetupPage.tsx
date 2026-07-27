import { CameraPreview } from '../../components/CameraPreview'
import { useAppStore } from '../../store/appStore'
import styles from './CameraSetupPage.module.css'

interface Props {
  cameraNum: 1 | 2
}

export function CameraSetupPage({ cameraNum }: Props) {
  const streamSession = useAppStore((s) => s.streamSession)
  const status = useAppStore((s) => s.status)
  const label =
    cameraNum === 1
      ? status?.camera_labels?.camera1 || 'Face-On'
      : status?.camera_labels?.camera2 || 'Down-the-Line'

  return (
    <section className={styles.page}>
      <CameraPreview
        cameraNum={cameraNum}
        active
        session={streamSession}
        label={`Camera ${cameraNum} (${label})`}
      />
      <p className={styles.note}>
        Property sliders and detect/reinit land in Phase B/C. Preview already
        disconnects when you leave this tab.
      </p>
    </section>
  )
}
