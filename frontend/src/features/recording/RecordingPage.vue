<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { api } from '../../api/client'
import type { ChecklistResponse } from '../../api/types'
import CameraPreview from '../../components/CameraPreview.vue'
import { useAppStore } from '../../store/appStore'
import AutoDetectPanel from './AutoDetectPanel.vue'
import ChecklistPanel from './ChecklistPanel.vue'
import PracticeTools from './PracticeTools.vue'
import styles from './RecordingPage.module.css'

const appStore = useAppStore()
const busy = ref(false)
const error = ref<string | null>(null)
const checklist = ref<ChecklistResponse | null>(null)
let checklistInterval: ReturnType<typeof setInterval> | undefined

const recording = computed(() => Boolean(appStore.status?.is_recording))
const autoOn = computed(() => Boolean(appStore.status?.auto_detect_enabled))
const label1 = computed(() => appStore.status?.camera_labels?.camera1 || 'Face-On')
const label2 = computed(() => appStore.status?.camera_labels?.camera2 || 'Down-the-Line')
const resolutionText = computed(
  () => `${appStore.status?.width || 1280}x${appStore.status?.height || 720} @ ${appStore.status?.fps || 120}fps`,
)

async function refreshChecklist() {
  try {
    checklist.value = await api.checklist()
  } catch {
    /* ignore */
  }
}

watch(
  () => [recording.value, appStore.status?.is_analyzing] as const,
  () => {
    if (checklistInterval) clearInterval(checklistInterval)
    checklistInterval = undefined
    void refreshChecklist()
    if (recording.value || appStore.status?.is_analyzing) return
    checklistInterval = setInterval(() => void refreshChecklist(), 2000)
  },
  { immediate: true },
)

watch(
  () => appStore.status?.is_analyzing,
  (isAnalyzing) => {
    if (isAnalyzing) appStore.setTab('analysis')
  },
)

onUnmounted(() => {
  if (checklistInterval) clearInterval(checklistInterval)
})

async function toggleRecord() {
  busy.value = true
  error.value = null
  try {
    const result = recording.value ? await api.stopRecording() : await api.startRecording()
    if (result.error) {
      error.value = result.error
      if ('checklist' in result && result.checklist) checklist.value = result.checklist
    } else if (!recording.value) {
      await refreshChecklist()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Recording failed'
  } finally {
    busy.value = false
  }
}

async function toggleAuto() {
  busy.value = true
  error.value = null
  try {
    const data = await api.toggleAutoDetect()
    if (data.error) {
      error.value = data.error
      if (data.checklist) checklist.value = data.checklist
    } else {
      await refreshChecklist()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Auto-detect failed'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section :class="styles.page">
    <div :class="[styles.dual, autoOn ? styles.autoActive : '']">
      <CameraPreview
        :camera-num="1"
        active
        :session="appStore.streamSession"
        :recording="recording"
        :label="`Camera 1 (${label1})`"
      />
      <CameraPreview
        :camera-num="2"
        active
        :session="appStore.streamSession"
        :recording="recording"
        :label="`Camera 2 (${label2})`"
      />
    </div>

    <div :class="styles.controls">
      <div :class="styles.statusRow">
        <span :class="[styles.dot, recording ? styles.dotLive : '']" />
        <div>
          <div :class="styles.label">
            {{ autoOn ? 'Auto-detect armed' : recording ? 'Recording' : 'Ready to record' }}
          </div>
          <div :class="styles.detail">{{ resolutionText }} &middot; Space to start/stop</div>
        </div>
        <span
          v-if="recording && appStore.status?.recording_duration != null"
          :class="styles.duration"
        >
          {{ appStore.status.recording_duration.toFixed(1) }}s
        </span>
      </div>

      <div :class="styles.buttons">
        <button
          v-if="!autoOn"
          type="button"
          :class="recording ? styles.stop : styles.start"
          :disabled="busy"
          @click="toggleRecord"
        >
          {{ recording ? 'Stop recording' : 'Start recording' }}
        </button>
        <label :class="styles.toggle">
          <input
            type="checkbox"
            :checked="autoOn"
            :disabled="busy || recording"
            @change="toggleAuto"
          />
          Auto detect
        </label>
      </div>

      <AutoDetectPanel :enabled="autoOn" :status="appStore.status?.auto_detect_status" />
      <p v-if="error" :class="styles.error">{{ error }}</p>
    </div>

    <ChecklistPanel :checklist="checklist" />
    <PracticeTools />
  </section>
</template>
