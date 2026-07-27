<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { api } from './api/client'
import AppHeader from './components/AppHeader.vue'
import TabBar from './components/TabBar.vue'
import { useStatusPoll } from './composables/useStatusPoll'
import AnalysisPage from './features/analysis/AnalysisPage.vue'
import ComparePage from './features/compare/ComparePage.vue'
import ProgressPage from './features/progress/ProgressPage.vue'
import RecordingPage from './features/recording/RecordingPage.vue'
import RecordingsPage from './features/recordings/RecordingsPage.vue'
import CameraSetupPage from './features/setup/CameraSetupPage.vue'
import SettingsPage from './features/settings/SettingsPage.vue'
import { TABS, useAppStore } from './store/appStore'
import styles from './App.module.css'

useStatusPoll()

const appStore = useAppStore()

function isFormField(target: EventTarget | null) {
  const tag = (target as HTMLElement | null)?.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

function onKey(event: KeyboardEvent) {
  if (isFormField(event.target)) return

  if (event.code === 'Space') {
    event.preventDefault()
    if (appStore.tab !== 'recording') appStore.setTab('recording')
    if (appStore.status?.auto_detect_enabled) return
    const recording = Boolean(appStore.status?.is_recording)
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

  const match = TABS.find((tab) => tab.shortcut === event.key)
  if (match) appStore.setTab(match.id)
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div :class="styles.app">
    <AppHeader />
    <TabBar />
    <main :class="styles.main" role="tabpanel">
      <CameraSetupPage v-if="appStore.tab === 'camera1'" :camera-num="1" />
      <CameraSetupPage v-else-if="appStore.tab === 'camera2'" :camera-num="2" />
      <RecordingPage v-else-if="appStore.tab === 'recording'" />
      <RecordingsPage v-else-if="appStore.tab === 'recordings'" />
      <AnalysisPage v-else-if="appStore.tab === 'analysis'" />
      <ComparePage v-else-if="appStore.tab === 'compare'" />
      <ProgressPage v-else-if="appStore.tab === 'progress'" />
      <SettingsPage v-else-if="appStore.tab === 'settings'" />
    </main>
  </div>
</template>
