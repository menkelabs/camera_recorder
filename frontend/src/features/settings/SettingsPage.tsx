import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { ArchiveStatus, PracticeSettings } from '../../api/types'
import { formatBytes } from '../../utils/format'
import styles from './SettingsPage.module.css'

export function SettingsPage() {
  const [practice, setPractice] = useState<PracticeSettings | null>(null)
  const [archivePath, setArchivePath] = useState('')
  const [archiveStatus, setArchiveStatus] = useState<ArchiveStatus | null>(null)
  const [configured, setConfigured] = useState(false)
  const [available, setAvailable] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [recCount, setRecCount] = useState(0)

  const refresh = async () => {
    const [p, cfg, st, recs] = await Promise.all([
      api.practiceSettings(),
      api.archiveConfig(),
      api.archiveStatus(),
      api.listRecordings(),
    ])
    setPractice(p)
    setArchivePath(cfg.archive_path || '')
    setConfigured(cfg.configured)
    setAvailable(cfg.available)
    setArchiveStatus(st)
    setRecCount(recs.count)
  }

  useEffect(() => {
    void refresh().catch((err) =>
      setMessage(err instanceof Error ? err.message : 'Failed to load settings'),
    )
  }, [])

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

  const role1 = practice?.camera_roles?.camera1 || 'face_on'
  const unarchived = Math.max(0, recCount - (archiveStatus?.archived_count || 0))
  const disk = archiveStatus?.disk || null

  return (
    <section className={styles.page}>
      <h2>Settings</h2>

      <div className={styles.card}>
        <h3>Camera roles</h3>
        <p className={styles.help}>
          Labels and scoring follow these roles. Swapping assigns the opposite role to the other camera.
        </p>
        <div className={styles.roles}>
          <label>
            Camera 1
            <select
              value={role1}
              disabled={busy}
              onChange={(e) =>
                void run(async () => {
                  const cam1 = e.target.value
                  const cam2 = cam1 === 'face_on' ? 'dtl' : 'face_on'
                  await api.updatePracticeSettings({
                    camera_roles: { camera1: cam1, camera2: cam2 },
                  })
                  setMessage('Camera roles updated')
                })
              }
            >
              <option value="face_on">Face-On</option>
              <option value="dtl">Down-the-Line</option>
            </select>
          </label>
          <div className={styles.rolePreview}>
            Cam1: <strong>{practice?.camera_labels?.camera1 || 'Face-On'}</strong>
            {' · '}
            Cam2: <strong>{practice?.camera_labels?.camera2 || 'Down-the-Line'}</strong>
          </div>
        </div>
      </div>

      <div className={styles.card}>
        <h3>Archive to external disk</h3>
        <p className={styles.help}>
          Configure a path (e.g. USB mount) to copy recordings, analysis JSON, and settings.
        </p>
        <div className={styles.archiveRow}>
          <input
            type="text"
            value={archivePath}
            placeholder="/media/user/Seagate8TB/golf"
            onChange={(e) => setArchivePath(e.target.value)}
          />
          <button
            type="button"
            disabled={busy || !archivePath.trim()}
            onClick={() =>
              void run(async () => {
                await api.setArchiveConfig(archivePath.trim())
                setMessage('Archive path saved')
              })
            }
          >
            Save path
          </button>
          <span
            className={
              !configured
                ? styles.badgeMuted
                : available
                  ? styles.badgeOk
                  : styles.badgeBad
            }
          >
            {!configured ? 'Not configured' : available ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        {disk && (
          <div className={styles.disk}>
            <div className={styles.diskBar}>
              <i style={{ width: `${Math.min(100, disk.percent || 0)}%` }} />
            </div>
            <p>
              {formatBytes(disk.used || 0)} used / {formatBytes(disk.total || 0)} total
              {' · '}
              {formatBytes(disk.free || 0)} free
            </p>
          </div>
        )}

        <div className={styles.archiveStats}>
          <span>
            <strong>{archiveStatus?.archived_count ?? 0}</strong> archived
          </span>
          <span>
            <strong>{unarchived}</strong> not yet archived
          </span>
          <button
            type="button"
            disabled={busy || !configured || !available || unarchived === 0}
            onClick={() =>
              void run(async () => {
                const res = await api.archiveRun()
                setMessage(
                  res.error
                    ? res.error
                    : `Archived ${res.archived_count ?? 0} recording(s)`,
                )
              })
            }
          >
            {unarchived > 0
              ? `Archive ${unarchived} new recording${unarchived === 1 ? '' : 's'}`
              : 'Nothing to archive'}
          </button>
        </div>
      </div>

      {message && <p className={styles.message}>{message}</p>}

      <p className={styles.footnote}>
        Full v1 UI remains at <a href="/legacy">/legacy</a> during cutover.
      </p>
    </section>
  )
}
