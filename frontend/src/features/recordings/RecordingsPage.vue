<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../../api/client'
import type { RecordingPair } from '../../api/types'
import { useAppStore } from '../../store/appStore'
import { formatBytes, formatDuration } from '../../utils/format'
import styles from './RecordingsPage.module.css'

type Filter = 'all' | 'favorites' | 'reference'

const appStore = useAppStore()
const rows = ref<RecordingPair[]>([])
const stats = ref({ count: 0, total_size: 0, favorites: 0, reference: null as string | null })
const selected = ref<Set<string>>(new Set())
const filter = ref<Filter>('all')
const cleanupDays = ref(30)
const message = ref<string | null>(null)
const editingNotes = ref<string | null>(null)
const notesDraft = ref('')
const busy = ref(false)
const filters: Filter[] = ['all', 'favorites', 'reference']

async function refresh() {
  const data = await api.listRecordings()
  rows.value = data.recordings || []
  stats.value = {
    count: data.count,
    total_size: data.total_size,
    favorites: data.favorite_count || 0,
    reference: data.reference_timestamp || null,
  }
}

onMounted(() => {
  void refresh().catch((err) => {
    message.value = err instanceof Error ? err.message : 'Failed to load recordings'
  })
})

const visible = computed(() => {
  if (filter.value === 'favorites') return rows.value.filter((row) => row.favorite)
  if (filter.value === 'reference') return rows.value.filter((row) => row.is_reference)
  return rows.value
})

function toggleSelect(timestamp: string) {
  const next = new Set(selected.value)
  if (next.has(timestamp)) next.delete(timestamp)
  else next.add(timestamp)
  selected.value = next
}

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

function updateCleanupDays(event: Event) {
  cleanupDays.value = Number((event.target as HTMLInputElement).value) || 30
}

function startEditing(row: RecordingPair) {
  editingNotes.value = row.timestamp
  notesDraft.value = row.notes || ''
}

async function deleteSelected() {
  await run(async () => {
    const res = await api.bulkDeleteRecordings([...selected.value])
    selected.value = new Set()
    message.value = `Deleted ${res.deleted_count}`
  })
}

async function cleanupOld() {
  await run(async () => {
    const res = await api.cleanupRecordings(cleanupDays.value)
    message.value = `Cleaned ${res.deleted_count} (before ${res.cutoff_date})`
  })
}

async function saveNotes(row: RecordingPair) {
  await run(async () => {
    await api.updateRecordingMeta(row.timestamp, { notes: notesDraft.value })
    editingNotes.value = null
  })
}

async function toggleFavorite(row: RecordingPair) {
  await run(async () => {
    await api.updateRecordingMeta(row.timestamp, { favorite: !row.favorite })
  })
}

async function toggleReference(row: RecordingPair) {
  await run(async () => {
    await api.setReference(row.is_reference ? null : row.timestamp)
    message.value = row.is_reference ? 'Reference cleared' : `Reference set to ${row.timestamp}`
  })
}

async function deleteRecording(row: RecordingPair) {
  await run(async () => {
    await api.deleteRecording(row.timestamp)
    const next = new Set(selected.value)
    next.delete(row.timestamp)
    selected.value = next
  })
}

async function claimRecording(row: RecordingPair) {
  await run(async () => {
    await api.claimRecording(row.timestamp)
    message.value = `Claimed ${row.timestamp}`
  })
}
</script>

<template>
  <section :class="styles.page">
    <div :class="styles.stats">
      <span><strong>{{ stats.count }}</strong> recordings</span>
      <span><strong>{{ formatBytes(stats.total_size) }}</strong> disk</span>
      <span><strong>{{ stats.favorites }}</strong> favorites</span>
      <span>Ref: <strong>{{ stats.reference || '-' }}</strong></span>
    </div>

    <div :class="styles.toolbar">
      <button type="button" :disabled="busy" @click="refresh">Refresh</button>
      <div :class="styles.filters">
        <button
          v-for="item in filters"
          :key="item"
          type="button"
          :class="filter === item ? styles.activeFilter : undefined"
          @click="filter = item"
        >
          {{ item }}
        </button>
      </div>
      <button
        type="button"
        :class="styles.danger"
        :disabled="busy || selected.size === 0"
        @click="deleteSelected"
      >
        Delete selected ({{ selected.size }})
      </button>
      <label :class="styles.cleanup">
        Older than
        <input type="number" min="1" max="365" :value="cleanupDays" @change="updateCleanupDays" />
        days
        <button type="button" :class="styles.danger" :disabled="busy" @click="cleanupOld">
          Clean up
        </button>
      </label>
    </div>

    <p v-if="message" :class="styles.message">{{ message }}</p>

    <div :class="styles.tableWrap">
      <table :class="styles.table">
        <thead>
          <tr>
            <th />
            <th>Date</th>
            <th>Duration</th>
            <th>Size</th>
            <th>Flags</th>
            <th>Notes</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="visible.length === 0">
            <td :colspan="7" :class="styles.empty">No recordings yet</td>
          </tr>
          <tr v-for="row in visible" :key="row.timestamp">
            <td>
              <input
                type="checkbox"
                :checked="selected.has(row.timestamp)"
                @change="toggleSelect(row.timestamp)"
              />
            </td>
            <td>
              <div>{{ row.date }}</div>
              <code>{{ row.timestamp }}</code>
            </td>
            <td>{{ formatDuration(row.duration) }}</td>
            <td>{{ formatBytes(row.total_size) }}</td>
            <td :class="styles.flags">
              <span v-if="row.favorite" title="Favorite">&#9733;</span>
              <span v-if="row.is_reference" title="Reference">REF</span>
              <span v-if="row.unclaimed" title="Unclaimed">OPEN</span>
            </td>
            <td :class="styles.notes">
              <div v-if="editingNotes === row.timestamp" :class="styles.notesEdit">
                <textarea v-model="notesDraft" rows="2" />
                <button type="button" :disabled="busy" @click="saveNotes(row)">Save</button>
              </div>
              <button v-else type="button" :class="styles.linkish" @click="startEditing(row)">
                {{ row.notes || 'Add note...' }}
              </button>
            </td>
            <td :class="styles.actions">
              <button
                v-if="row.unclaimed"
                type="button"
                :disabled="busy"
                @click="claimRecording(row)"
              >
                Claim
              </button>
              <button type="button" :disabled="busy" @click="toggleFavorite(row)">
                {{ row.favorite ? 'Unstar' : 'Star' }}
              </button>
              <button type="button" :disabled="busy" @click="toggleReference(row)">
                {{ row.is_reference ? 'Clear ref' : 'Set ref' }}
              </button>
              <button type="button" title="Open Compare tab" @click="appStore.setTab('compare')">
                Compare
              </button>
              <button
                type="button"
                :class="styles.danger"
                :disabled="busy"
                @click="deleteRecording(row)"
              >
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
