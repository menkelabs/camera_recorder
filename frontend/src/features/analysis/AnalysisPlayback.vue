<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { analysisFrameUrl, api } from '../../api/client'
import { PlaybackSequencer, playIntervalMs } from './playbackSequencer'
import styles from './AnalysisPlayback.module.css'

const SPEEDS = [0.25, 0.5, 1, 2, 4]

interface Props {
  maxFrames: number
  initialIndex?: number
}

const props = withDefaults(defineProps<Props>(), {
  initialIndex: 0,
})

const emit = defineEmits<{
  results: [data: unknown]
}>()

const index = ref(props.initialIndex)
const playing = ref(false)
const speedIdx = ref(2)
const bust = ref(0)
let sequencer: PlaybackSequencer | null = null
let timer: ReturnType<typeof setTimeout> | undefined

const speed = computed(() => SPEEDS[speedIdx.value])
const urls = computed(() => ({
  cam1: analysisFrameUrl(1, index.value, bust.value),
  cam2: analysisFrameUrl(2, index.value, bust.value),
}))

function clearPlaybackTimer() {
  if (timer) clearTimeout(timer)
  timer = undefined
}

function scheduleTick() {
  clearPlaybackTimer()
  if (!playing.value || props.maxFrames <= 1) return

  const tick = () => {
    const next = index.value + 1
    if (next >= props.maxFrames) {
      playing.value = false
      return
    }
    sequencer?.request(next)
    timer = setTimeout(tick, playIntervalMs(speed.value))
  }

  timer = setTimeout(tick, playIntervalMs(speed.value))
}

function togglePlaying() {
  playing.value = !playing.value
}

function cycleSpeed() {
  speedIdx.value = (speedIdx.value + 1) % SPEEDS.length
}

function step(delta: number) {
  if (props.maxFrames <= 0) return
  playing.value = false
  const next = Math.max(0, Math.min(props.maxFrames - 1, index.value + delta))
  sequencer?.request(next)
}

function onSeek(event: Event) {
  playing.value = false
  sequencer?.request(Number((event.target as HTMLInputElement).value))
}

function isFormField(target: EventTarget | null) {
  const tag = (target as HTMLElement | null)?.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

function onKey(event: KeyboardEvent) {
  if (isFormField(event.target) || props.maxFrames <= 0) return
  if (event.code === 'Space') {
    event.preventDefault()
    togglePlaying()
    return
  }
  if (event.key === 'ArrowLeft' || event.key === 'a' || event.key === 'A') {
    event.preventDefault()
    step(-1)
    return
  }
  if (event.key === 'ArrowRight' || event.key === 'd' || event.key === 'D') {
    event.preventDefault()
    step(1)
  }
}

onMounted(() => {
  sequencer = new PlaybackSequencer(
    async (frameIndex) => {
      const data = await api.setAnalysisFrame(frameIndex)
      emit('results', data)
      bust.value += 1
    },
    (frameIndex) => {
      index.value = frameIndex
    },
  )
  window.addEventListener('keydown', onKey)
})

watch([playing, speed, () => props.maxFrames], scheduleTick)

onUnmounted(() => {
  clearPlaybackTimer()
  sequencer?.dispose()
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div v-if="maxFrames <= 0" :class="styles.empty">
    No annotated frames yet - record and analyze a swing.
  </div>
  <div v-else :class="styles.wrap">
    <div :class="styles.dual">
      <img :src="urls.cam1" alt="Camera 1 analysis" />
      <img :src="urls.cam2" alt="Camera 2 analysis" />
    </div>
    <div :class="styles.controls">
      <button type="button" @click="togglePlaying">{{ playing ? 'Pause' : 'Play' }}</button>
      <button type="button" @click="cycleSpeed">{{ speed }}x</button>
      <input
        type="range"
        min="0"
        :max="Math.max(0, maxFrames - 1)"
        :value="index"
        @input="onSeek"
      />
      <span :class="styles.meta">{{ index + 1 }} / {{ maxFrames }}</span>
    </div>
    <p :class="styles.hint">Space play/pause · ←/A prev · →/D next</p>
  </div>
</template>
