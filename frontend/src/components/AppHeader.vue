<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api/client'
import type { LocalUser } from '../api/types'
import { useAppStore } from '../store/appStore'
import styles from './AppHeader.module.css'

const appStore = useAppStore()

const recording = computed(() => appStore.status?.is_recording)
const analyzing = computed(() => appStore.status?.is_analyzing)
const cams = computed(() => appStore.status?.cameras_available)
const message = computed(() => appStore.statusError || appStore.status?.status_message)

const users = computed(() => appStore.status?.users || [])
const activeUser = computed(() => appStore.status?.active_user || null)
const selectedId = ref<number | ''>('')
const pin = ref('')
const needsPin = ref(false)
const switchError = ref<string | null>(null)
const switching = ref(false)

watch(
  activeUser,
  (user) => {
    selectedId.value = user?.id ?? ''
    needsPin.value = false
    pin.value = ''
    switchError.value = null
  },
  { immediate: true },
)

function onSelectUser(event: Event) {
  const id = Number((event.target as HTMLSelectElement).value)
  selectedId.value = id
  const target = users.value.find((u) => u.id === id)
  needsPin.value = Boolean(target?.has_pin && target.id !== activeUser.value?.id)
  pin.value = ''
  switchError.value = null
  if (!needsPin.value && target && target.id !== activeUser.value?.id) {
    void switchTo(target)
  }
}

async function switchTo(target: LocalUser) {
  if (recording.value) {
    switchError.value = 'Stop recording before switching users'
    selectedId.value = activeUser.value?.id ?? ''
    return
  }
  switching.value = true
  switchError.value = null
  try {
    const res = await api.setActiveUser(
      target.id,
      needsPin.value ? pin.value : undefined,
    )
    if (appStore.status) {
      appStore.setStatus({
        ...appStore.status,
        active_user: res.active_user,
        users: res.users,
      })
    }
    needsPin.value = false
    pin.value = ''
  } catch (err) {
    switchError.value = err instanceof Error ? err.message : 'Could not switch user'
    selectedId.value = activeUser.value?.id ?? ''
  } finally {
    switching.value = false
  }
}

async function confirmPin() {
  const target = users.value.find((u) => u.id === selectedId.value)
  if (!target) return
  await switchTo(target)
}
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
    <div :class="styles.userSwitch" aria-label="Active player">
      <label>
        Player
        <select
          :value="selectedId"
          :disabled="switching || Boolean(recording) || users.length === 0"
          @change="onSelectUser"
        >
          <option v-for="user in users" :key="user.id" :value="user.id">
            {{ user.name }}{{ user.has_pin ? ' · PIN' : '' }}
          </option>
        </select>
      </label>
      <template v-if="needsPin">
        <input
          v-model="pin"
          type="password"
          inputmode="numeric"
          autocomplete="off"
          placeholder="PIN"
          :disabled="switching"
          @keydown.enter="confirmPin"
        />
        <button type="button" :disabled="switching || !pin" @click="confirmPin">
          Unlock
        </button>
      </template>
      <span
        v-if="activeUser"
        :class="styles.userChip"
        :style="activeUser.color ? { borderColor: activeUser.color } : undefined"
      >
        {{ activeUser.name }}
      </span>
    </div>
    <div v-if="switchError || message" :class="styles.message" role="status">
      {{ switchError || message }}
    </div>
  </header>
</template>
