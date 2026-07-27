import { useEffect } from 'react'
import { AppHeader } from './components/AppHeader'
import { TabBar } from './components/TabBar'
import { AnalysisPage } from './features/analysis/AnalysisPage'
import { PlaceholderPage } from './features/PlaceholderPage'
import { RecordingPage } from './features/recording/RecordingPage'
import { CameraSetupPage } from './features/setup/CameraSetupPage'
import { useStatusPoll } from './hooks/useStatusPoll'
import { TABS, useAppStore } from './store/appStore'
import styles from './App.module.css'

export default function App() {
  useStatusPoll()
  const tab = useAppStore((s) => s.tab)
  const setTab = useAppStore((s) => s.setTab)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      const match = TABS.find((t) => t.shortcut === e.key)
      if (match) setTab(match.id)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setTab])

  return (
    <div className={styles.app}>
      <AppHeader />
      <TabBar />
      <main className={styles.main} role="tabpanel">
        {tab === 'camera1' && <CameraSetupPage cameraNum={1} />}
        {tab === 'camera2' && <CameraSetupPage cameraNum={2} />}
        {tab === 'recording' && <RecordingPage />}
        {tab === 'recordings' && <PlaceholderPage title="Recordings" />}
        {tab === 'analysis' && <AnalysisPage />}
        {tab === 'compare' && <PlaceholderPage title="Compare" />}
        {tab === 'progress' && <PlaceholderPage title="Progress" />}
        {tab === 'settings' && <PlaceholderPage title="Settings" />}
      </main>
    </div>
  )
}
