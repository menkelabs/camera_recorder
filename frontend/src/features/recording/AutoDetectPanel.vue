<script setup lang="ts">
import { computed } from 'vue'
import type { AutoDetectStatus } from '../../api/types'
import styles from './AutoDetectPanel.module.css'

interface Props {
  enabled: boolean
  status?: AutoDetectStatus
}

const props = defineProps<Props>()

const state = computed(() => (props.status?.state || 'idle').replace(/_/g, ' '))
const delta = computed(() => props.status?.delta)
const threshold = computed(() => props.status?.motion_threshold || 15)
const pct = computed(() =>
  delta.value != null ? Math.min(100, (Number(delta.value) / (threshold.value * 2)) * 100) : 0,
)

const badgeClass = computed(() => {
  if (props.status?.state === 'motion_detected') return styles.motion
  if (props.status?.state === 'recording') return styles.recording
  if (props.status?.state === 'cooldown') return styles.cooldown
  return styles.idle
})
</script>

<template>
  <div v-if="enabled" :class="styles.panel">
    <div :class="styles.row">
      <span :class="[styles.badge, badgeClass]">{{ state }}</span>
      <span :class="styles.info">Watching for swing...</span>
    </div>
    <div :class="styles.gauge">
      <span :class="styles.gaugeLabel">Shoulder turn &Delta;</span>
      <div :class="styles.barBg">
        <div :class="styles.barFill" :style="{ width: `${pct}%` }" />
      </div>
      <span :class="styles.gaugeValue">
        {{ delta != null ? `${Number(delta).toFixed(1)}deg` : '-' }}
      </span>
    </div>
  </div>
</template>
