<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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
const indexDraft = ref(0)

watch(
  cameraIndex,
  (value) => {
    if (typeof value === 'number') indexDraft.value = value
  },
  { immediate: true },
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
    const id = Number(indexDraft.value)
    if (!Number.isInteger(id) || id < 0) {
      message.value = 'Device index must be a non-negative integer'
      return
    }
    const otherId = props.cameraNum === 1 ? appStore.status?.camera2_id : appStore.status?.camera1_id
    const body =
      props.cameraNum === 1
        ? { camera1_id: id, ...(otherId != null ? { camera2_id: otherId } : {}) }
        : { camera2_id: id, ...(otherId != null ? { camera1_id: otherId } : {}) }
    await api.reinitCameras(body)
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
    <p v-if="appStore.status && !appStore.status.cameras_available" :class="styles.warn">
      Cameras offline — plug them in, then use Detect or Reinit.
    </p>
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
        <label :class="styles.index">
          Device index
          <input
            v-model.number="indexDraft"
            type="number"
            min="0"
            step="1"
          >
        </label>
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
