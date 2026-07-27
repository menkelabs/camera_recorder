<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api/client'
import type { AnalysisListItem, CompareResponse } from '../../api/types'
import LineChart from '../../components/LineChart.vue'
import styles from './ComparePage.module.css'

const CAM1_KEYS = [
  'max_sway_left',
  'max_sway_right',
  'max_head_sway_left',
  'max_head_sway_right',
  'tempo_ratio',
  'address_knee_flex',
]
const CAM2_KEYS = [
  'max_shoulder_turn',
  'max_hip_turn',
  'max_x_factor',
  'address_spine_angle',
  'min_lead_arm_angle',
]

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

const analyses = ref<AnalysisListItem[]>([])
const a = ref('')
const b = ref('')
const data = ref<CompareResponse | null>(null)
const metric = ref('shoulder_turn')
const error = ref<string | null>(null)
const loading = ref(false)

const chartSeries = computed(() => {
  if (!data.value) return []
  const sa = seriesFromSwing(data.value.swing_a, 'camera2', metric.value)
  const sb = seriesFromSwing(data.value.swing_b, 'camera2', metric.value)
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

onMounted(() => {
  void api
    .listAnalyses()
    .then((res) => {
      analyses.value = res.analyses || []
      const reference = res.reference_timestamp
      const list = res.analyses || []
      if (list.length) {
        a.value =
          reference && list.some((item) => item.timestamp === reference)
            ? reference
            : list[0].timestamp
        b.value = list[Math.min(1, list.length - 1)].timestamp
      }
    })
    .catch((err) => {
      error.value = err instanceof Error ? err.message : 'Failed to load analyses'
    })
})

async function runCompare() {
  if (!a.value || !b.value) return
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
      <button type="button" :disabled="loading || !a || !b" @click="runCompare">
        {{ loading ? 'Comparing...' : 'Refresh' }}
      </button>
    </div>

    <p v-if="error" :class="styles.error">{{ error }}</p>
    <p v-if="!analyses.length" :class="styles.empty">
      No saved analyses yet - record and analyze first.
    </p>

    <template v-if="data">
      <div :class="styles.deltas">
        <div :class="styles.card">
          <h3>Camera 1 (Face-On)</h3>
          <p v-if="!data.deltas.camera1" :class="styles.empty">No summary data</p>
          <div v-else :class="styles.deltaGrid">
            <template v-for="key in CAM1_KEYS" :key="key">
              <div v-if="data.deltas.camera1[key]" :class="styles.deltaItem">
                <span>{{ metricLabel(key) }}</span>
                <strong>{{ fmt(data.deltas.camera1[key].a) }} -&gt; {{ fmt(data.deltas.camera1[key].b) }}</strong>
                <em :class="deltaClass(data.deltas.camera1[key].delta)">
                  {{
                    data.deltas.camera1[key].delta == null
                      ? '-'
                      : `${data.deltas.camera1[key].delta > 0 ? '+' : ''}${data.deltas.camera1[
                          key
                        ].delta.toFixed(1)}`
                  }}
                </em>
              </div>
            </template>
          </div>
        </div>
        <div :class="styles.card">
          <h3>Camera 2 (DTL)</h3>
          <p v-if="!data.deltas.camera2" :class="styles.empty">No summary data</p>
          <div v-else :class="styles.deltaGrid">
            <template v-for="key in CAM2_KEYS" :key="key">
              <div v-if="data.deltas.camera2[key]" :class="styles.deltaItem">
                <span>{{ metricLabel(key) }}</span>
                <strong>{{ fmt(data.deltas.camera2[key].a) }} -&gt; {{ fmt(data.deltas.camera2[key].b) }}</strong>
                <em :class="deltaClass(data.deltas.camera2[key].delta)">
                  {{
                    data.deltas.camera2[key].delta == null
                      ? '-'
                      : `${data.deltas.camera2[key].delta > 0 ? '+' : ''}${data.deltas.camera2[
                          key
                        ].delta.toFixed(1)}`
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
