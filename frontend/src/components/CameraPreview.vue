<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import styles from './CameraPreview.module.css'

interface Props {
  cameraNum: 1 | 2
  /** When false, MJPEG src is cleared so the browser drops the stream. */
  active: boolean
  /** Bump after reinit/detect to force reconnect. */
  session?: number
  label?: string
  recording?: boolean
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  session: 0,
  recording: false,
  label: undefined,
  className: undefined,
})

const src = ref('')

function refreshSource(forceBust = false) {
  if (!props.active || document.hidden) {
    src.value = ''
    return
  }

  const bust = forceBust ? `&r=${Date.now()}` : ''
  src.value = `/video_feed/${props.cameraNum}?s=${props.session}${bust}`
}

watch(
  () => [props.active, props.cameraNum, props.session] as const,
  () => refreshSource(),
  { immediate: true },
)

function onVisibility() {
  refreshSource(true)
}

onMounted(() => {
  document.addEventListener('visibilitychange', onVisibility)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibility)
  src.value = ''
})
</script>

<template>
  <div :class="[styles.card, className]">
    <div :class="styles.frame">
      <img v-if="src" :src="src" :alt="label || `Camera ${cameraNum}`" />
      <div v-else :class="styles.placeholder">Feed paused</div>
      <span v-if="recording && active" :class="styles.recBadge">REC</span>
    </div>
    <div v-if="label" :class="styles.label">{{ label }}</div>
  </div>
</template>
