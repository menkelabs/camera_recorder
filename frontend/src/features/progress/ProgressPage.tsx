import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import type { ProgressResponse } from '../../api/types'
import { LineChart } from '../../components/LineChart'
import styles from './ProgressPage.module.css'

const COLORS = ['#58a6ff', '#3fb950', '#f0883e', '#d2a8ff', '#79c0ff', '#f85149', '#d29922']

export function ProgressPage() {
  const [data, setData] = useState<ProgressResponse | null>(null)
  const [enabled, setEnabled] = useState<Record<string, boolean>>({ score: true })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void api
      .progress()
      .then((res) => {
        setData(res)
        const next: Record<string, boolean> = {}
        for (const m of res.metrics || []) {
          next[m.key] = m.key === 'score'
        }
        setEnabled(next)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load progress'))
  }, [])

  const series = useMemo(() => {
    if (!data) return []
    return (data.metrics || [])
      .filter((m) => enabled[m.key])
      .map((m, i) => ({
        label: m.label,
        color: COLORS[i % COLORS.length],
        values: data.series[m.key] || [],
      }))
  }, [data, enabled])

  const labels = useMemo(
    () => (data?.points || []).map((p) => p.date || p.timestamp || ''),
    [data],
  )

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2>Progress</h2>
          <p>Trends across saved analyses (oldest → newest).</p>
        </div>
        {data && (
          <div className={styles.summary}>
            <span>
              Swings: <strong>{data.count}</strong>
            </span>
            <span>
              Latest:{' '}
              <strong>
                {data.latest_grade || '—'}{' '}
                {data.latest_score != null ? Math.round(data.latest_score) : ''}
              </strong>
            </span>
            <span>
              Δ score:{' '}
              <strong
                className={
                  data.score_delta == null
                    ? undefined
                    : data.score_delta >= 0
                      ? styles.up
                      : styles.down
                }
              >
                {data.score_delta == null
                  ? '—'
                  : `${data.score_delta > 0 ? '+' : ''}${data.score_delta}`}
              </strong>
            </span>
          </div>
        )}
      </header>

      {error && <p className={styles.error}>{error}</p>}

      {data && (
        <>
          <div className={styles.toggles}>
            {(data.metrics || []).map((m, i) => (
              <label key={m.key}>
                <input
                  type="checkbox"
                  checked={Boolean(enabled[m.key])}
                  onChange={(e) =>
                    setEnabled((prev) => ({ ...prev, [m.key]: e.target.checked }))
                  }
                />
                <i style={{ background: COLORS[i % COLORS.length] }} />
                {m.label}
              </label>
            ))}
          </div>
          <LineChart series={series} labels={labels} height={300} />
          {!data.count && (
            <p className={styles.empty}>No analyzed swings yet — progress appears after analysis JSON is saved.</p>
          )}
        </>
      )}
    </section>
  )
}
