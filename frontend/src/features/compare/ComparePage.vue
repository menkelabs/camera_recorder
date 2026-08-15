<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api/client'
import type { AnalysisListItem, CompareResponse, PracticeSettings } from '../../api/types'
import LineChart from '../../components/LineChart.vue'
import { useAppStore } from '../../store/appStore'
import styles from './ComparePage.module.css'

const FACE_ON_KEYS = [
  'max_sway_left',
  'max_sway_right',
  'max_head_sway_left',
  'max_head_sway_right',
  'tempo_ratio',
  'address_knee_flex',
]
const DTL_KEYS = [
  'max_shoulder_turn',
  'max_hip_turn',
  'max_x_factor',
  'address_spine_angle',
  'min_lead_arm_angle',
]
const FACE_ON_METRICS = new Set(['sway'])

function seriesFromSwing(
  swing: Record<string, unknown> | undefined,
  cam: 'camera1' | 'camera2',
  key: string,
): Array<number | null> {
  const block = (swing?.[cam] || {}) as Record<string, unknown>
  const arr = block[key]
  if (!Array.isArray(arr)) return []
  return arr.map((v) => (typeof v === 'number' ? v : null))
}

const appStore = useAppStore()
const analyses = ref<AnalysisListItem[]>([])
const settings = ref<PracticeSettings | null>(null)
const a = ref('')
const b = ref('')
const data = ref<CompareResponse | null>(null)
const metric = ref('shoulder_turn')
const error = ref<string | null>(null)
const loading = ref(false)

const sameSwing = computed(() => Boolean(a.value && b.value && a.value === b.value))
const faceOnCam = computed<'camera1' | 'camera2'>(() =>
  settings.value?.camera_roles?.camera1 === 'dtl' ? 'camera2' : 'camera1',
)
const dtlCam = computed<'camera1' | 'camera2'>(() =>
  faceOnCam.value === 'camera1' ? 'camera2' : 'camera1',
)
const faceOnLabel = computed(
  () => settings.value?.camera_labels?.[faceOnCam.value] || 'Face-On',
)
const dtlLabel = computed(
  () => settings.value?.camera_labels?.[dtlCam.value] || 'Down-the-Line',
)
const faceOnDeltas = computed(() => data.value?.deltas[faceOnCam.value] || null)
const dtlDeltas = computed(() => data.value?.deltas[dtlCam.value] || null)

const chartSeries = computed(() => {
  if (!data.value) return []
  const cam = FACE_ON_METRICS.has(metric.value) ? faceOnCam.value : dtlCam.value
  const sa = seriesFromSwing(data.value.swing_a, cam, metric.value)
  const sb = seriesFromSwing(data.value.swing_b, cam, metric.value)
  const n = Math.max(sa.length, sb.length, 1)
  const norm = (arr: Array<number | null>) => {
    if (arr.length === 0) return Array.from({ length: n }, () => null)
    return Array.from({ length: n }, (_, i) => {
      const src = Math.round((i / Math.max(n - 1, 1)) * (arr.length - 1))
      return arr[src] ?? null
    })
  }
  return [
    { label: `A - ${a.value}`, color: '#58a6ff', values: norm(sa) },
    { label: `B - ${b.value}`, color: '#3fb950', values: norm(sb), dashed: true },
  ]
})

function pickDefaults(list: AnalysisListItem[], reference?: string | null) {
  const prefill = appStore.comparePrefill
  const timestamps = list.map((item) => item.timestamp)
  const preferredA =
    (prefill?.a && timestamps.includes(prefill.a) && prefill.a) ||
    (reference && timestamps.includes(reference) && reference) ||
    list[0]?.timestamp ||
    ''
  const preferredB =
    (prefill?.b && timestamps.includes(prefill.b) && prefill.b !== preferredA && prefill.b) ||
    list.find((item) => item.timestamp !== preferredA)?.timestamp ||
    ''
  a.value = preferredA
  b.value = preferredB
  if (prefill) appStore.setComparePrefill(null)
}

onMounted(() => {
  void Promise.all([api.listAnalyses(), api.practiceSettings()])
    .then(([res, practice]) => {
      analyses.value = res.analyses || []
      settings.value = practice
      pickDefaults(res.analyses || [], res.reference_timestamp)
    })
    .catch((err) => {
      error.value = err instanceof Error ? err.message : 'Failed to load analyses'
    })
})

async function runCompare() {
  if (!a.value || !b.value || sameSwing.value) return
  loading.value = true
  error.value = null
  try {
    data.value = await api.compare(a.value, b.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Compare failed'
    data.value = null
  } finally {
    loading.value = false
  }
}

watch([a, b], ([nextA, nextB], _previous, onCleanup) => {
  if (!nextA || !nextB) return
  if (nextA === nextB) {
    data.value = null
    error.value = 'Same swing — select two different swings.'
    return
  }
  let cancelled = false
  onCleanup(() => {
    cancelled = true
  })
  loading.value = true
  error.value = null
  void api
    .compare(nextA, nextB)
    .then((res) => {
      if (!cancelled) data.value = res
    })
    .catch((err) => {
      if (!cancelled) {
        error.value = err instanceof Error ? err.message : 'Compare failed'
        data.value = null
      }
    })
    .finally(() => {
      if (!cancelled) loading.value = false
    })
})

function fmt(value: number | null | undefined) {
  return value == null ? '-' : Number(value).toFixed(1)
}

function deltaClass(delta: number | null | undefined) {
  if (delta == null) return ''
  if (delta > 0) return styles.up
  if (delta < 0) return styles.down
  return styles.flat
}

function metricLabel(value: string) {
  return value.replace(/_/g, ' ')
}
</script>

<template>
  <section :class="styles.page">
    <header :class="styles.header">
      <h2>Compare Swings</h2>
      <p>Pick two saved analyses. Reference swing is preferred as A when set.</p>
    </header>

    <div :class="styles.pickers">
      <label>
        Swing A
        <select v-model="a">
          <option v-for="item in analyses" :key="item.timestamp" :value="item.timestamp">
            {{ item.date }}{{ item.is_reference ? ' - REF' : '' }}
          </option>
        </select>
      </label>
      <label>
        Swing B
        <select v-model="b">
          <option v-for="item in analyses" :key="item.timestamp" :value="item.timestamp">
            {{ item.date }}{{ item.is_reference ? ' - REF' : '' }}
          </option>
        </select>
      </label>
      <button type="button" :disabled="loading || !a || !b || sameSwing" @click="runCompare">
        {{ loading ? 'Comparing...' : 'Refresh' }}
      </button>
    </div>

    <p v-if="error" :class="styles.error">{{ error }}</p>
    <p v-if="!analyses.length" :class="styles.empty">
      No saved analyses yet - record and analyze first.
    </p>
    <p v-else-if="analyses.length === 1" :class="styles.empty">
      Only one analyzed swing so far — record another to compare.
    </p>

    <template v-if="data && !sameSwing">
      <div :class="styles.deltas">
        <div :class="styles.card">
          <h3>{{ faceOnLabel }}</h3>
          <p v-if="!faceOnDeltas" :class="styles.empty">No summary data</p>
          <div v-else :class="styles.deltaGrid">
            <template v-for="key in FACE_ON_KEYS" :key="key">
              <div v-if="faceOnDeltas[key]" :class="styles.deltaItem">
                <span>{{ metricLabel(key) }}</span>
                <strong>{{ fmt(faceOnDeltas[key].a) }} -&gt; {{ fmt(faceOnDeltas[key].b) }}</strong>
                <em :class="deltaClass(faceOnDeltas[key].delta)">
                  {{
                    faceOnDeltas[key].delta == null
                      ? '-'
                      : `${faceOnDeltas[key].delta > 0 ? '+' : ''}${faceOnDeltas[key].delta.toFixed(1)}`
                  }}
                </em>
              </div>
            </template>
          </div>
        </div>
        <div :class="styles.card">
          <h3>{{ dtlLabel }}</h3>
          <p v-if="!dtlDeltas" :class="styles.empty">No summary data</p>
          <div v-else :class="styles.deltaGrid">
            <template v-for="key in DTL_KEYS" :key="key">
              <div v-if="dtlDeltas[key]" :class="styles.deltaItem">
                <span>{{ metricLabel(key) }}</span>
                <strong>{{ fmt(dtlDeltas[key].a) }} -&gt; {{ fmt(dtlDeltas[key].b) }}</strong>
                <em :class="deltaClass(dtlDeltas[key].delta)">
                  {{
                    dtlDeltas[key].delta == null
                      ? '-'
                      : `${dtlDeltas[key].delta > 0 ? '+' : ''}${dtlDeltas[key].delta.toFixed(1)}`
                  }}
                </em>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div :class="styles.chartBlock">
        <div :class="styles.chartHead">
          <h3>Overlay (normalized timeline)</h3>
          <select v-model="metric">
            <option value="shoulder_turn">Shoulder turn</option>
            <option value="hip_turn">Hip turn</option>
            <option value="x_factor">X-factor</option>
            <option value="sway">Sway</option>
          </select>
        </div>
        <LineChart :series="chartSeries" :y-label="metricLabel(metric)" />
      </div>
    </template>
  </section>
</template>
