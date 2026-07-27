<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '../store/appStore'
import styles from './AppHeader.module.css'

const appStore = useAppStore()

const recording = computed(() => appStore.status?.is_recording)
const analyzing = computed(() => appStore.status?.is_analyzing)
const cams = computed(() => appStore.status?.cameras_available)
const message = computed(() => appStore.statusError || appStore.status?.status_message)
</script>

<template>
  <header :class="styles.header">
    <div>
      <p :class="styles.brand">SwingLab</p>
      <h1>Camera Setup &amp; Recording</h1>
    </div>
    <div :class="styles.badges">
      <span :class="[styles.badge, cams ? styles.ok : styles.warn]">
        {{ cams ? 'Cameras ready' : 'Cameras offline' }}
      </span>
      <span v-if="recording" :class="[styles.badge, styles.rec]">Recording</span>
      <span v-if="analyzing" :class="[styles.badge, styles.info]">Analyzing</span>
      <span v-if="appStore.status?.fps != null" :class="styles.badge">
        Target {{ appStore.status.fps }} fps
      </span>
    </div>
    <div v-if="message" :class="styles.message" role="status">
      {{ message }}
    </div>
  </header>
</template>
