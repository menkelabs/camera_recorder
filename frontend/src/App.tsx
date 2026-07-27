import { useEffect } from 'react'
import { api } from './api/client'
import { AppHeader } from './components/AppHeader'
import { TabBar } from './components/TabBar'
import { AnalysisPage } from './features/analysis/AnalysisPage'
import { ComparePage } from './features/compare/ComparePage'
import { ProgressPage } from './features/progress/ProgressPage'
import { RecordingPage } from './features/recording/RecordingPage'
import { RecordingsPage } from './features/recordings/RecordingsPage'
import { CameraSetupPage } from './features/setup/CameraSetupPage'
import { SettingsPage } from './features/settings/SettingsPage'
import { useStatusPoll } from './hooks/useStatusPoll'
import { TABS, useAppStore } from './store/appStore'
import styles from './App.module.css'

export default function App() {
  useStatusPoll()
  const tab = useAppStore((s) => s.tab)
  const setTab = useAppStore((s) => s.setTab)
  const status = useAppStore((s) => s.status)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

      if (e.code === 'Space') {
        e.preventDefault()
        if (tab !== 'recording') setTab('recording')
        if (status?.auto_detect_enabled) return
        const recording = Boolean(status?.is_recording)
        void (async () => {
          try {
            if (recording) await api.stopRecording()
            else await api.startRecording()
          } catch {
            /* status poll will surface messages */
          }
        })()
        return
      }

      const match = TABS.find((t) => t.shortcut === e.key)
      if (match) setTab(match.id)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setTab, tab, status?.auto_detect_enabled, status?.is_recording])

  return (
    <div className={styles.app}>
      <AppHeader />
      <TabBar />
      <main className={styles.main} role="tabpanel">
        {tab === 'camera1' && <CameraSetupPage cameraNum={1} />}
        {tab === 'camera2' && <CameraSetupPage cameraNum={2} />}
        {tab === 'recording' && <RecordingPage />}
        {tab === 'recordings' && <RecordingsPage />}
        {tab === 'analysis' && <AnalysisPage />}
        {tab === 'compare' && <ComparePage />}
        {tab === 'progress' && <ProgressPage />}
        {tab === 'settings' && <SettingsPage />}
      </main>
    </div>
  )
}
