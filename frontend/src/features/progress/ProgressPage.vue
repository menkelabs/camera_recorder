<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../../api/client'
import type { ProgressResponse } from '../../api/types'
import LineChart from '../../components/LineChart.vue'
import styles from './ProgressPage.module.css'

const COLORS = ['#58a6ff', '#3fb950', '#f0883e', '#d2a8ff', '#79c0ff', '#f85149', '#d29922']

const data = ref<ProgressResponse | null>(null)
const enabled = ref<Record<string, boolean>>({ score: true })
const error = ref<string | null>(null)

const series = computed(() => {
  if (!data.value) return []
  return (data.value.metrics || [])
    .filter((metric) => enabled.value[metric.key])
    .map((metric, index) => ({
      label: metric.label,
      color: COLORS[index % COLORS.length],
      values: data.value?.series[metric.key] || [],
    }))
})

const labels = computed(() => (data.value?.points || []).map((point) => point.date || point.timestamp || ''))

onMounted(() => {
  void api
    .progress()
    .then((res) => {
      data.value = res
      const next: Record<string, boolean> = {}
      for (const metric of res.metrics || []) {
        next[metric.key] =
          metric.key === 'score' ||
          metric.key === 'max_shoulder_turn' ||
          metric.key === 'tempo_ratio'
      }
      enabled.value = next
    })
    .catch((err) => {
      error.value = err instanceof Error ? err.message : 'Failed to load progress'
    })
})

function setMetricEnabled(key: string, event: Event) {
  enabled.value = {
    ...enabled.value,
    [key]: (event.target as HTMLInputElement).checked,
  }
}
</script>

<template>
  <section :class="styles.page">
    <header :class="styles.header">
      <div>
        <h2>Progress</h2>
        <p>Trends across saved analyses (oldest -&gt; newest).</p>
      </div>
      <div v-if="data" :class="styles.summary">
        <span>Swings: <strong>{{ data.count }}</strong></span>
        <span>
          Latest:
          <strong>
            {{ data.latest_grade || '-' }}
            {{ data.latest_score != null ? Math.round(data.latest_score) : '' }}
          </strong>
        </span>
        <span>
          &Delta; score:
          <strong
            :class="
              data.score_delta == null
                ? undefined
                : data.score_delta >= 0
                  ? styles.up
                  : styles.down
            "
          >
            {{
              data.score_delta == null
                ? '-'
                : `${data.score_delta > 0 ? '+' : ''}${data.score_delta}`
            }}
          </strong>
        </span>
      </div>
    </header>

    <p v-if="error" :class="styles.error">{{ error }}</p>

    <template v-if="data && data.count > 0">
      <div :class="styles.toggles">
        <label v-for="(metric, index) in data.metrics || []" :key="metric.key">
          <input
            type="checkbox"
            :checked="Boolean(enabled[metric.key])"
            @change="setMetricEnabled(metric.key, $event)"
          />
          <i :style="{ background: COLORS[index % COLORS.length] }" />
          {{ metric.label }}
        </label>
      </div>
      <LineChart :series="series" :labels="labels" :height="300" />
    </template>
    <p v-else-if="data && !data.count" :class="styles.empty">
      No analyzed swings yet - progress appears after analysis JSON is saved.
    </p>
  </section>
</template>
