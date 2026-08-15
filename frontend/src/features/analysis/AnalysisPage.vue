<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../../api/client'
import type { AnalysisListItem, AnalysisResults, AnalysisScore } from '../../api/types'
import { useAppStore } from '../../store/appStore'
import AnalysisPlayback from './AnalysisPlayback.vue'
import styles from './AnalysisPage.module.css'

type MetricValue = number | string | null | undefined
type MetricCurrent = Record<string, MetricValue>

const appStore = useAppStore()
const results = ref<AnalysisResults | null>(null)
const score = ref<AnalysisScore | null>(null)
const analyses = ref<AnalysisListItem[]>([])
const selectedTs = ref('')
const error = ref<string | null>(null)
const exportMsg = ref<string | null>(null)
const exportBusy = ref(false)
let pollInterval: ReturnType<typeof setInterval> | undefined

const cam1 = computed(() => results.value?.camera1)
const phase = computed(() => cam1.value?.current?.phase)
const hasFrames = computed(() =>
  Boolean(results.value && results.value.max_frames > 0 && results.value.has_frames && !results.value.is_analyzing),
)
const isSaved = computed(() => results.value?.source === 'saved' && !hasFrames.value)

const metricBlocks = computed(() => [
  {
    title: cam1Title.value,
    detection: cam1.value?.detection_rate,
    current: cam1.value?.current,
    keys: ['sway', 'head_sway', 'spine_tilt', 'knee_flex', 'weight_shift'],
  },
  {
    title: cam2Title.value,
    detection: results.value?.camera2?.detection_rate,
    current: results.value?.camera2?.current,
    keys: ['shoulder_turn', 'hip_turn', 'x_factor', 'spine_angle', 'lead_arm_angle'],
  },
])

const hasMetricData = computed(() => Boolean(cam1.value || results.value?.camera2))
const focusAreas = computed(() => score.value?.focus_areas || score.value?.focus || [])
const hasCoach = computed(() => Boolean(focusAreas.value.length || score.value?.strengths?.length))
const cam1Title = computed(() => results.value?.camera_labels?.camera1 || 'Camera 1')
const cam2Title = computed(() => results.value?.camera_labels?.camera2 || 'Camera 2')
const canExport = computed(() => hasMetricData.value && !results.value?.is_analyzing)

async function loadAnalyses() {
  try {
    const res = await api.listAnalyses()
    analyses.value = res.analyses || []
  } catch {
    analyses.value = []
  }
}

async function refresh() {
  try {
    const data = await api.analysisResults(selectedTs.value || undefined)
    results.value = data
    error.value = null
    if (data.score) {
      score.value = data.score
    } else if (!data.is_analyzing && (data.max_frames > 0 || data.camera1 || data.camera2)) {
      try {
        score.value = await api.analysisScore(selectedTs.value || undefined)
      } catch {
        score.value = null
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load analysis'
  }
}

onMounted(() => {
  const prefill = appStore.analysisPrefill
  if (prefill) {
    selectedTs.value = prefill
    appStore.setAnalysisPrefill(null)
  }
  void loadAnalyses()
  void refresh()
})

watch(selectedTs, () => {
  void refresh()
})

watch(
  () => results.value?.is_analyzing,
  (isAnalyzing) => {
    if (pollInterval) clearInterval(pollInterval)
    pollInterval = undefined
    if (isAnalyzing) pollInterval = setInterval(() => void refresh(), 1000)
  },
)

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

function downloadReport(format: 'html' | 'csv') {
  exportMsg.value = null
  window.location.assign(api.analysisExportUrl(format, selectedTs.value || undefined))
}

async function downloadClip(camera: 1 | 2) {
  exportBusy.value = true
  exportMsg.value = null
  try {
    const data = await api.exportClip(camera, 30, selectedTs.value || undefined)
    if (data.error || !data.filename) {
      exportMsg.value = data.error || 'Clip export failed'
      return
    }
    window.location.assign(api.analysisClipUrl(data.filename))
    exportMsg.value = `Saved ${data.filename}`
  } catch (err) {
    exportMsg.value = err instanceof Error ? err.message : 'Clip export failed'
  } finally {
    exportBusy.value = false
  }
}

function formatMetric(current: MetricCurrent, key: string) {
  const value = current[key]
  if (value == null || value === '') return '-'
  return typeof value === 'number' ? Number(value).toFixed(1) : String(value)
}
</script>

<template>
  <section :class="styles.page">
    <header :class="styles.header">
      <div>
        <h2>Analysis</h2>
        <span v-if="phase != null" :class="styles.phase">{{ String(phase) }}</span>
      </div>
      <div :class="styles.headerRight">
        <label :class="styles.picker">
          Swing
          <select v-model="selectedTs" :disabled="Boolean(results?.is_analyzing)">
            <option value="">Latest session</option>
            <option v-for="item in analyses" :key="item.timestamp" :value="item.timestamp">
              {{ item.date }}{{ item.is_reference ? ' - REF' : '' }}
            </option>
          </select>
        </label>
        <div v-if="score?.score != null" :class="styles.score">
          <span :class="styles.grade">{{ score.grade || '-' }}</span>
          <span :class="styles.scoreNum">{{ Math.round(Number(score.score)) }}</span>
        </div>
        <div v-if="canExport" :class="styles.exportActions" role="group" aria-label="Export analysis">
          <button type="button" @click="downloadReport('html')">Export HTML</button>
          <button type="button" @click="downloadReport('csv')">Export CSV</button>
          <button v-if="hasFrames" type="button" :disabled="exportBusy" @click="downloadClip(1)">
            Clip Cam1
          </button>
          <button v-if="hasFrames" type="button" :disabled="exportBusy" @click="downloadClip(2)">
            Clip Cam2
          </button>
        </div>
      </div>
    </header>
    <p v-if="exportMsg" :class="styles.exportMsg">{{ exportMsg }}</p>
    <p v-if="isSaved" :class="styles.savedNote">
      Saved swing — score and metrics from disk. Playback frames are only available for the latest session.
    </p>

    <p v-if="results?.is_analyzing" :class="styles.progress">
      {{ results.progress || 'Analyzing...' }}
    </p>
    <p v-if="error || results?.analysis_error" :class="styles.error">
      {{ error || results?.analysis_error }}
    </p>

    <AnalysisPlayback
      :max-frames="hasFrames ? results?.max_frames || 0 : 0"
      :initial-index="results?.frame_index || 0"
      @results="results = $event as AnalysisResults"
    />

    <div v-if="hasMetricData" :class="styles.metrics">
      <div v-for="block in metricBlocks" :key="block.title" :class="styles.block">
        <template v-if="block.current">
          <h3>
            {{ block.title }}
            <span v-if="block.detection != null" :class="styles.det">
              {{ block.detection.toFixed(0) }}% det
            </span>
          </h3>
          <div :class="styles.grid">
            <div v-for="key in block.keys" :key="key" :class="styles.metric">
              <span>{{ key.replace(/_/g, ' ') }}</span>
              <strong>{{ formatMetric(block.current, key) }}</strong>
            </div>
          </div>
        </template>
        <template v-else>
          <h3>{{ block.title }}</h3>
          <p :class="styles.muted">No data</p>
        </template>
      </div>
    </div>

    <div v-if="score && hasCoach" :class="styles.coach">
      <div v-if="score.strengths?.length">
        <h4>Strengths</h4>
        <ul>
          <li v-for="item in score.strengths" :key="item">{{ item }}</li>
        </ul>
      </div>
      <div v-if="focusAreas.length">
        <h4>Focus</h4>
        <ul>
          <li v-for="item in focusAreas" :key="item">{{ item }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>
