import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import type { RecordingPair } from '../../api/types'
import { useAppStore } from '../../store/appStore'
import { formatBytes, formatDuration } from '../../utils/format'
import styles from './RecordingsPage.module.css'

export function RecordingsPage() {
  const setTab = useAppStore((s) => s.setTab)
  const [rows, setRows] = useState<RecordingPair[]>([])
  const [stats, setStats] = useState({ count: 0, total_size: 0, favorites: 0, reference: null as string | null })
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<'all' | 'favorites' | 'reference'>('all')
  const [cleanupDays, setCleanupDays] = useState(30)
  const [message, setMessage] = useState<string | null>(null)
  const [editingNotes, setEditingNotes] = useState<string | null>(null)
  const [notesDraft, setNotesDraft] = useState('')
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async () => {
    const data = await api.listRecordings()
    setRows(data.recordings || [])
    setStats({
      count: data.count,
      total_size: data.total_size,
      favorites: data.favorite_count || 0,
      reference: data.reference_timestamp || null,
    })
  }, [])

  useEffect(() => {
    void refresh().catch((err) =>
      setMessage(err instanceof Error ? err.message : 'Failed to load recordings'),
    )
  }, [refresh])

  const visible = useMemo(() => {
    if (filter === 'favorites') return rows.filter((r) => r.favorite)
    if (filter === 'reference') return rows.filter((r) => r.is_reference)
    return rows
  }, [rows, filter])

  const toggleSelect = (ts: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(ts)) next.delete(ts)
      else next.add(ts)
      return next
    })
  }

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setMessage(null)
    try {
      await fn()
      await refresh()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className={styles.page}>
      <div className={styles.stats}>
        <span>
          <strong>{stats.count}</strong> recordings
        </span>
        <span>
          <strong>{formatBytes(stats.total_size)}</strong> disk
        </span>
        <span>
          <strong>{stats.favorites}</strong> favorites
        </span>
        <span>
          Ref: <strong>{stats.reference || '—'}</strong>
        </span>
      </div>

      <div className={styles.toolbar}>
        <button type="button" disabled={busy} onClick={() => void refresh()}>
          Refresh
        </button>
        <div className={styles.filters}>
          {(['all', 'favorites', 'reference'] as const).map((f) => (
            <button
              key={f}
              type="button"
              className={filter === f ? styles.activeFilter : undefined}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={styles.danger}
          disabled={busy || selected.size === 0}
          onClick={() =>
            void run(async () => {
              const res = await api.bulkDeleteRecordings([...selected])
              setSelected(new Set())
              setMessage(`Deleted ${res.deleted_count}`)
            })
          }
        >
          Delete selected ({selected.size})
        </button>
        <label className={styles.cleanup}>
          Older than
          <input
            type="number"
            min={1}
            max={365}
            value={cleanupDays}
            onChange={(e) => setCleanupDays(Number(e.target.value) || 30)}
          />
          days
          <button
            type="button"
            className={styles.danger}
            disabled={busy}
            onClick={() =>
              void run(async () => {
                const res = await api.cleanupRecordings(cleanupDays)
                setMessage(`Cleaned ${res.deleted_count} (before ${res.cutoff_date})`)
              })
            }
          >
            Clean up
          </button>
        </label>
      </div>

      {message && <p className={styles.message}>{message}</p>}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
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
            {visible.length === 0 && (
              <tr>
                <td colSpan={7} className={styles.empty}>
                  No recordings yet
                </td>
              </tr>
            )}
            {visible.map((r) => (
              <tr key={r.timestamp}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(r.timestamp)}
                    onChange={() => toggleSelect(r.timestamp)}
                  />
                </td>
                <td>
                  <div>{r.date}</div>
                  <code>{r.timestamp}</code>
                </td>
                <td>{formatDuration(r.duration)}</td>
                <td>{formatBytes(r.total_size)}</td>
                <td className={styles.flags}>
                  {r.favorite && <span title="Favorite">★</span>}
                  {r.is_reference && <span title="Reference">REF</span>}
                </td>
                <td className={styles.notes}>
                  {editingNotes === r.timestamp ? (
                    <div className={styles.notesEdit}>
                      <textarea
                        value={notesDraft}
                        onChange={(e) => setNotesDraft(e.target.value)}
                        rows={2}
                      />
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          void run(async () => {
                            await api.updateRecordingMeta(r.timestamp, {
                              notes: notesDraft,
                            })
                            setEditingNotes(null)
                          })
                        }
                      >
                        Save
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className={styles.linkish}
                      onClick={() => {
                        setEditingNotes(r.timestamp)
                        setNotesDraft(r.notes || '')
                      }}
                    >
                      {r.notes || 'Add note…'}
                    </button>
                  )}
                </td>
                <td className={styles.actions}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await api.updateRecordingMeta(r.timestamp, {
                          favorite: !r.favorite,
                        })
                      })
                    }
                  >
                    {r.favorite ? 'Unstar' : 'Star'}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await api.setReference(r.is_reference ? null : r.timestamp)
                        setMessage(
                          r.is_reference
                            ? 'Reference cleared'
                            : `Reference set to ${r.timestamp}`,
                        )
                      })
                    }
                  >
                    {r.is_reference ? 'Clear ref' : 'Set ref'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setTab('compare')}
                    title="Open Compare tab"
                  >
                    Compare
                  </button>
                  <button
                    type="button"
                    className={styles.danger}
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await api.deleteRecording(r.timestamp)
                        setSelected((prev) => {
                          const next = new Set(prev)
                          next.delete(r.timestamp)
                          return next
                        })
                      })
                    }
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
