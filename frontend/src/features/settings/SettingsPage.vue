<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../../api/client'
import type { ArchiveStatus, PracticeSettings } from '../../api/types'
import { formatBytes } from '../../utils/format'
import styles from './SettingsPage.module.css'

const practice = ref<PracticeSettings | null>(null)
const archivePath = ref('')
const archiveStatus = ref<ArchiveStatus | null>(null)
const configured = ref(false)
const available = ref(false)
const message = ref<string | null>(null)
const busy = ref(false)
const recCount = ref(0)

const role1 = computed(() => practice.value?.camera_roles?.camera1 || 'face_on')
const unarchived = computed(() => Math.max(0, recCount.value - (archiveStatus.value?.archived_count || 0)))
const disk = computed(() => archiveStatus.value?.disk || null)

async function refresh() {
  const [settings, config, status, recordings] = await Promise.all([
    api.practiceSettings(),
    api.archiveConfig(),
    api.archiveStatus(),
    api.listRecordings(),
  ])
  practice.value = settings
  archivePath.value = config.archive_path || ''
  configured.value = config.configured
  available.value = config.available
  archiveStatus.value = status
  recCount.value = recordings.count
}

onMounted(() => {
  void refresh().catch((err) => {
    message.value = err instanceof Error ? err.message : 'Failed to load settings'
  })
})

async function run(fn: () => Promise<void>) {
  busy.value = true
  message.value = null
  try {
    await fn()
    await refresh()
  } catch (err) {
    message.value = err instanceof Error ? err.message : 'Action failed'
  } finally {
    busy.value = false
  }
}

async function updateCameraRoles(event: Event) {
  await run(async () => {
    const cam1 = (event.target as HTMLSelectElement).value
    const cam2 = cam1 === 'face_on' ? 'dtl' : 'face_on'
    await api.updatePracticeSettings({
      camera_roles: { camera1: cam1, camera2: cam2 },
    })
    message.value = 'Camera roles updated'
  })
}

async function saveArchivePath() {
  await run(async () => {
    await api.setArchiveConfig(archivePath.value.trim())
    message.value = 'Archive path saved'
  })
}

async function archiveNew() {
  await run(async () => {
    const res = await api.archiveRun()
    message.value = res.error
      ? res.error
      : `Archived ${res.archived_count ?? 0} recording(s)`
  })
}
</script>

<template>
  <section :class="styles.page">
    <h2>Settings</h2>

    <div :class="styles.card">
      <h3>Camera roles</h3>
      <p :class="styles.help">
        Labels and scoring follow these roles. Swapping assigns the opposite role to the other camera.
      </p>
      <div :class="styles.roles">
        <label>
          Camera 1
          <select :value="role1" :disabled="busy" @change="updateCameraRoles">
            <option value="face_on">Face-On</option>
            <option value="dtl">Down-the-Line</option>
          </select>
        </label>
        <div :class="styles.rolePreview">
          Cam1: <strong>{{ practice?.camera_labels?.camera1 || 'Face-On' }}</strong>
          &middot;
          Cam2: <strong>{{ practice?.camera_labels?.camera2 || 'Down-the-Line' }}</strong>
        </div>
      </div>
    </div>

    <div :class="styles.card">
      <h3>Archive to external disk</h3>
      <p :class="styles.help">
        Configure a path (e.g. USB mount) to copy recordings, analysis JSON, and settings.
      </p>
      <div :class="styles.archiveRow">
        <input
          v-model="archivePath"
          type="text"
          placeholder="/media/user/Seagate8TB/golf"
        />
        <button type="button" :disabled="busy || !archivePath.trim()" @click="saveArchivePath">
          Save path
        </button>
        <span
          :class="
            !configured ? styles.badgeMuted : available ? styles.badgeOk : styles.badgeBad
          "
        >
          {{ !configured ? 'Not configured' : available ? 'Connected' : 'Disconnected' }}
        </span>
      </div>

      <div v-if="disk" :class="styles.disk">
        <div :class="styles.diskBar">
          <i :style="{ width: `${Math.min(100, disk.percent || 0)}%` }" />
        </div>
        <p>
          {{ formatBytes(disk.used || 0) }} used / {{ formatBytes(disk.total || 0) }} total
          &middot;
          {{ formatBytes(disk.free || 0) }} free
        </p>
      </div>

      <div :class="styles.archiveStats">
        <span><strong>{{ archiveStatus?.archived_count ?? 0 }}</strong> archived</span>
        <span><strong>{{ unarchived }}</strong> not yet archived</span>
        <button
          type="button"
          :disabled="busy || !configured || !available || unarchived === 0"
          @click="archiveNew"
        >
          {{
            unarchived > 0
              ? `Archive ${unarchived} new recording${unarchived === 1 ? '' : 's'}`
              : 'Nothing to archive'
          }}
        </button>
      </div>
    </div>

    <p v-if="message" :class="styles.message">{{ message }}</p>

    <p :class="styles.footnote">
      Full v1 UI remains at <a href="/legacy">/legacy</a> during cutover.
    </p>
  </section>
</template>
