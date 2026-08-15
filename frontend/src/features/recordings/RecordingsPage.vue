<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../../api/client'
import type { RecordingPair } from '../../api/types'
import { useAppStore } from '../../store/appStore'
import { formatBytes, formatDuration } from '../../utils/format'
import styles from './RecordingsPage.module.css'

type Filter = 'all' | 'favorites' | 'reference'
type Scope = 'mine' | 'unclaimed' | 'all'

const FILTER_LABELS: Record<Filter, string> = {
  all: 'All',
  favorites: '★ Favorites',
  reference: 'Reference',
}
const SCOPE_LABELS: Record<Scope, string> = {
  mine: 'Mine',
  unclaimed: 'Unclaimed',
  all: 'Everyone',
}

const appStore = useAppStore()
const rows = ref<RecordingPair[]>([])
const stats = ref({ count: 0, total_size: 0, favorites: 0, reference: null as string | null })
const selected = ref<Set<string>>(new Set())
const filter = ref<Filter>('all')
const scope = ref<Scope>('mine')
const cleanupDays = ref(30)
const message = ref<string | null>(null)
const editingNotes = ref<string | null>(null)
const notesDraft = ref('')
const tagsDraft = ref('')
const busy = ref(false)
const filters: Filter[] = ['all', 'favorites', 'reference']
const scopes: Scope[] = ['mine', 'unclaimed', 'all']

async function refresh() {
  const data = await api.listRecordings({ scope: scope.value })
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

const emptyLabel = computed(() => {
  if (rows.value.length === 0) return 'No recordings yet'
  return 'No recordings match this filter'
})

function canDelete(row: RecordingPair) {
  return row.owned_by_me !== false || Boolean(row.unclaimed)
}

function toggleSelect(timestamp: string) {
  const row = rows.value.find((item) => item.timestamp === timestamp)
  if (row && !canDelete(row)) return
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
  tagsDraft.value = (row.tags || []).join(', ')
}

function parseTags(raw: string): string[] {
  return raw
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
}

async function setScope(next: Scope) {
  scope.value = next
  await run(async () => undefined)
}

async function deleteSelected() {
  const targets = [...selected.value].filter((ts) => {
    const row = rows.value.find((item) => item.timestamp === ts)
    return !row || canDelete(row)
  })
  if (targets.length === 0) return
  if (!window.confirm(`Delete ${targets.length} recording(s)? This cannot be undone.`)) return
  await run(async () => {
    const res = await api.bulkDeleteRecordings(targets)
    selected.value = new Set()
    const skipped = res.skipped_count ? ` (kept ${res.skipped_count})` : ''
    message.value = `Deleted ${res.deleted_count}${skipped}`
  })
}

async function cleanupOld() {
  if (
    !window.confirm(
      `Delete your recordings and unclaimed files older than ${cleanupDays.value} days? Favorites and the reference swing are kept.`,
    )
  ) {
    return
  }
  await run(async () => {
    const res = await api.cleanupRecordings(cleanupDays.value)
    const skipped = res.skipped_count ? ` (kept ${res.skipped_count})` : ''
    message.value = `Cleaned ${res.deleted_count}${skipped} (before ${res.cutoff_date})`
  })
}

async function saveNotes(row: RecordingPair) {
  await run(async () => {
    await api.updateRecordingMeta(row.timestamp, {
      notes: notesDraft.value,
      tags: parseTags(tagsDraft.value),
    })
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
  if (!window.confirm(`Delete recording ${row.date}? This cannot be undone.`)) return
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

function openCompare(row: RecordingPair) {
  appStore.setComparePrefill({ a: row.timestamp })
  appStore.setTab('compare')
}

function openAnalysis(row: RecordingPair) {
  appStore.setAnalysisPrefill(row.timestamp)
  appStore.setTab('analysis')
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
      <div :class="styles.filters" role="group" aria-label="Recording scope">
        <button
          v-for="item in scopes"
          :key="item"
          type="button"
          :class="scope === item ? styles.activeFilter : undefined"
          @click="setScope(item)"
        >
          {{ SCOPE_LABELS[item] }}
        </button>
      </div>
      <div :class="styles.filters" role="group" aria-label="Recording filters">
        <button
          v-for="item in filters"
          :key="item"
          type="button"
          :class="filter === item ? styles.activeFilter : undefined"
          @click="filter = item"
        >
          {{ FILTER_LABELS[item] }}
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
        <button
          type="button"
          :class="styles.danger"
          :disabled="busy"
          aria-label="Clean up old recordings"
          @click="cleanupOld"
        >
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
            <th>Player</th>
            <th>Flags</th>
            <th>Notes</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="visible.length === 0">
            <td :colspan="8" :class="styles.empty">{{ emptyLabel }}</td>
          </tr>
          <tr v-for="row in visible" :key="row.timestamp">
            <td>
              <input
                type="checkbox"
                :checked="selected.has(row.timestamp)"
                :disabled="!canDelete(row)"
                :title="canDelete(row) ? 'Select for delete' : 'Another player owns this recording'"
                @change="toggleSelect(row.timestamp)"
              />
            </td>
            <td>
              <div>{{ row.date }}</div>
              <code>{{ row.timestamp }}</code>
            </td>
            <td>{{ formatDuration(row.duration) }}</td>
            <td>{{ formatBytes(row.total_size) }}</td>
            <td>{{ row.unclaimed ? 'Unclaimed' : row.owner_name || '—' }}</td>
            <td :class="styles.flags">
              <span v-if="row.favorite" title="Favorite">&#9733;</span>
              <span v-if="row.is_reference" title="Reference">REF</span>
              <span v-if="row.unclaimed" title="Unclaimed">OPEN</span>
            </td>
            <td :class="styles.notes">
              <div v-if="editingNotes === row.timestamp" :class="styles.notesEdit">
                <textarea v-model="notesDraft" rows="2" placeholder="Notes" />
                <input v-model="tagsDraft" type="text" placeholder="Tags, comma-separated" />
                <button type="button" :disabled="busy" @click="saveNotes(row)">Save</button>
              </div>
              <button v-else type="button" :class="styles.linkish" @click="startEditing(row)">
                {{ row.notes || (row.tags && row.tags.length ? row.tags.join(', ') : 'Add note...') }}
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
              <button
                v-if="row.has_analysis"
                type="button"
                title="Open Analysis tab"
                @click="openAnalysis(row)"
              >
                Analyze
              </button>
              <button type="button" title="Open Compare tab" @click="openCompare(row)">
                Compare
              </button>
              <button
                v-if="canDelete(row)"
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
