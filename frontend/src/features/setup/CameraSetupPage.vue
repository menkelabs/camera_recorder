<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../../api/client'
import CameraPreview from '../../components/CameraPreview.vue'
import PropertySliders from '../../components/PropertySliders.vue'
import { useAppStore } from '../../store/appStore'
import styles from './CameraSetupPage.module.css'

interface Props {
  cameraNum: 1 | 2
}

const props = defineProps<Props>()
const appStore = useAppStore()
const message = ref<string | null>(null)
const busy = ref(false)

const roleLabel = computed(() =>
  props.cameraNum === 1
    ? appStore.status?.camera_labels?.camera1 || 'Face-On'
    : appStore.status?.camera_labels?.camera2 || 'Down-the-Line',
)

const cameraIndex = computed(() =>
  props.cameraNum === 1 ? appStore.status?.camera1_id ?? '?' : appStore.status?.camera2_id ?? '?',
)

const previewLabel = computed(
  () => `Camera ${props.cameraNum} (${roleLabel.value}) \u00b7 index ${cameraIndex.value}`,
)

async function run(fn: () => Promise<void>) {
  busy.value = true
  message.value = null
  try {
    await fn()
  } catch (err) {
    message.value = err instanceof Error ? err.message : 'Action failed'
  } finally {
    busy.value = false
  }
}

async function saveSettings() {
  await run(async () => {
    const res = await api.saveSettings()
    message.value = res.success ? `Saved ${res.filename}` : res.error || 'Save failed'
  })
}

async function resetDefaults() {
  await run(async () => {
    await api.resetCamera(props.cameraNum)
    message.value = `Camera ${props.cameraNum} reset to defaults`
  })
}

async function reinitCameras() {
  await run(async () => {
    await api.reinitCameras()
    appStore.bumpStreamSession()
    message.value = 'Cameras re-initialized'
  })
}

async function detectCameras() {
  await run(async () => {
    const res = await api.detectCameras()
    appStore.bumpStreamSession()
    message.value =
      `Found indices [${res.available_indices.join(', ')}] \u00b7 ` +
      `using ${res.camera1_id}/${res.camera2_id}`
  })
}
</script>

<template>
  <section :class="styles.page">
    <div :class="styles.layout">
      <CameraPreview
        :camera-num="cameraNum"
        active
        :session="appStore.streamSession"
        :label="previewLabel"
      />
      <div :class="styles.controls">
        <h3>Properties</h3>
        <PropertySliders :camera-num="cameraNum" active />
        <div :class="styles.actions">
          <button type="button" :disabled="busy" @click="saveSettings">Save settings</button>
          <button type="button" :disabled="busy" @click="resetDefaults">Reset defaults</button>
          <button type="button" :disabled="busy" @click="reinitCameras">Reinit</button>
          <button type="button" :disabled="busy" @click="detectCameras">Detect</button>
        </div>
        <p v-if="message" :class="styles.message">{{ message }}</p>
      </div>
    </div>
  </section>
</template>
