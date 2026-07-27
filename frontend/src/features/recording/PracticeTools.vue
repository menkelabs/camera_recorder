<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../../api/client'
import { useMetronome } from '../../composables/useMetronome'
import { useAppStore } from '../../store/appStore'
import styles from './PracticeTools.module.css'

const appStore = useAppStore()
const session = computed(() => appStore.status?.session)
const bpm = ref(60)
const metroOn = ref(false)
const message = ref<string | null>(null)
const { beatAccent, pulse } = useMetronome(bpm, metroOn)

watch(
  () => appStore.status?.practice?.metronome?.bpm,
  (serverBpm) => {
    if (serverBpm) bpm.value = serverBpm
    // Do not auto-start audio from server settings; browsers require a user gesture.
  },
)

async function persistMetro(enabled: boolean, nextBpm: number) {
  try {
    await api.updatePracticeSettings({
      metronome: { enabled, bpm: nextBpm, ratio: '3:1' },
    })
  } catch {
    /* ignore */
  }
}

async function toggleSession(enabled: boolean) {
  message.value = null
  try {
    const res = await api.setSessionEnabled(enabled)
    if (res.error) message.value = res.error
    else if (enabled) appStore.setTab('recording')
  } catch (err) {
    message.value = err instanceof Error ? err.message : 'Session toggle failed'
  }
}

async function nextSwing() {
  message.value = null
  try {
    const res = await api.sessionNext()
    if (res.error) message.value = res.error
  } catch (err) {
    message.value = err instanceof Error ? err.message : 'Next swing failed'
  }
}

function onMetroToggle(event: Event) {
  const on = (event.target as HTMLInputElement).checked
  metroOn.value = on
  void persistMetro(on, bpm.value)
}

function onBpmChange(event: Event) {
  const value = Number((event.target as HTMLInputElement).value) || 60
  const next = Math.min(120, Math.max(40, value))
  bpm.value = next
  void persistMetro(metroOn.value, next)
}
</script>

<template>
  <div :class="styles.panel">
    <h3>Practice Tools</h3>
    <div :class="styles.row">
      <label :class="styles.toggle">
        <input
          type="checkbox"
          :checked="Boolean(session?.enabled)"
          @change="toggleSession(($event.target as HTMLInputElement).checked)"
        />
        Session mode
      </label>
      <span :class="styles.meta">{{ session?.phase || 'idle' }}</span>
      <span :class="styles.meta">swings: {{ session?.count ?? 0 }}</span>
      <button
        v-if="session?.enabled && session.phase === 'review'"
        type="button"
        @click="nextSwing"
      >
        Next swing
      </button>
    </div>
    <div :class="styles.row">
      <label :class="styles.toggle">
        <input type="checkbox" :checked="metroOn" @change="onMetroToggle" />
        Tempo metronome
      </label>
      <span
        :key="pulse"
        :class="[styles.beat, metroOn ? (beatAccent ? styles.accent : styles.pulse) : '']"
      />
      <label :class="styles.bpm">
        BPM
        <input type="number" min="40" max="120" :value="bpm" @change="onBpmChange" />
      </label>
      <span :class="styles.meta">3:1 feel</span>
    </div>
    <p v-if="message" :class="styles.error">{{ message }}</p>
  </div>
</template>
