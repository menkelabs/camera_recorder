<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { api, formatPropValue } from '../api/client'
import type { CameraProperties } from '../api/types'
import { PROP_ORDER } from '../api/types'
import styles from './PropertySliders.module.css'

interface Props {
  cameraNum: 1 | 2
  active: boolean
}

const props = defineProps<Props>()

const cameraProps = ref<CameraProperties | null>(null)
const error = ref<string | null>(null)
const local = ref<Record<string, number>>({})
const debounce: Record<string, ReturnType<typeof setTimeout>> = {}
let intervalId: ReturnType<typeof setInterval> | undefined

async function refresh() {
  try {
    const data = await api.cameraProperties(props.cameraNum)
    if (data.error) {
      error.value = data.error
      cameraProps.value = null
      return
    }

    error.value = null
    cameraProps.value = data
    const next: Record<string, number> = {}
    for (const name of PROP_ORDER) {
      const item = data[name]
      if (item) next[name] = item.value
    }
    local.value = next
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load properties'
  }
}

const info = computed(() => cameraProps.value?._info)

const rows = computed(() => {
  const data = cameraProps.value
  if (!data) return []
  return PROP_ORDER.filter((name) => data[name]).map((name) => ({
    name,
    ...data[name],
    value: local.value[name] ?? data[name].value,
  }))
})

function onChange(name: string, value: number) {
  local.value = { ...local.value, [name]: value }
  clearTimeout(debounce[name])
  debounce[name] = setTimeout(() => {
    void api.setCameraProperty(props.cameraNum, name, value).catch(() => {})
  }, 50)
}

watch(
  () => [props.active, props.cameraNum] as const,
  () => {
    if (intervalId) clearInterval(intervalId)
    intervalId = undefined
    if (!props.active) return
    void refresh()
    intervalId = setInterval(() => void refresh(), 2000)
  },
  { immediate: true },
)

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
  for (const id of Object.values(debounce)) clearTimeout(id)
})
</script>

<template>
  <div v-if="error" :class="styles.error">{{ error }}</div>
  <div v-else-if="!cameraProps" :class="styles.loading">Loading properties...</div>
  <div v-else :class="styles.wrap">
    <p v-if="info" :class="styles.info">
      {{ info.width }}x{{ info.height }} @ {{ Number(info.fps || 0).toFixed(1) }} fps
    </p>
    <div :class="styles.list">
      <label v-for="row in rows" :key="row.name" :class="styles.row">
        <span :class="styles.label">{{ row.name.replace('_', ' ') }}</span>
        <input
          type="range"
          :min="row.min"
          :max="row.max"
          :step="row.step"
          :value="row.value"
          @input="onChange(row.name, Number(($event.target as HTMLInputElement).value))"
        />
        <span :class="styles.value">{{ formatPropValue(row.name, row.value) }}</span>
      </label>
    </div>
  </div>
</template>
