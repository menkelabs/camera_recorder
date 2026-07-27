import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import type { AnalysisListItem, CompareDelta, CompareResponse } from '../../api/types'
import { LineChart } from '../../components/LineChart'
import styles from './ComparePage.module.css'

const CAM1_KEYS = [
  'max_sway_left',
  'max_sway_right',
  'max_head_sway_left',
  'max_head_sway_right',
  'tempo_ratio',
  'address_knee_flex',
]
const CAM2_KEYS = [
  'max_shoulder_turn',
  'max_hip_turn',
  'max_x_factor',
  'address_spine_angle',
  'min_lead_arm_angle',
]

function seriesFromSwing(
  swing: Record<string, unknown> | undefined,
  cam: 'camera1' | 'camera2',
  key: string,
): Array<number | null> {
  const block = (swing?.[cam] || {}) as {
    [k: string]: unknown
  }
  const arr = block[key]
  if (!Array.isArray(arr)) return []
  return arr.map((v) => (typeof v === 'number' ? v : null))
}

export function ComparePage() {
  const [analyses, setAnalyses] = useState<AnalysisListItem[]>([])
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const [data, setData] = useState<CompareResponse | null>(null)
  const [metric, setMetric] = useState('shoulder_turn')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    void api
      .listAnalyses()
      .then((res) => {
        setAnalyses(res.analyses || [])
        const ref = res.reference_timestamp
        const list = res.analyses || []
        if (list.length) {
          setA(ref && list.some((x) => x.timestamp === ref) ? ref : list[0].timestamp)
          setB(list[Math.min(1, list.length - 1)].timestamp)
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load analyses'))
  }, [])

  const runCompare = async () => {
    if (!a || !b) return
    setLoading(true)
    setError(null)
    try {
      setData(await api.compare(a, b))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Compare failed')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!a || !b) return
    let cancelled = false
    setLoading(true)
    setError(null)
    void api
      .compare(a, b)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Compare failed')
          setData(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [a, b])

  const chartSeries = useMemo(() => {
    if (!data) return []
    const sa = seriesFromSwing(data.swing_a, 'camera2', metric)
    const sb = seriesFromSwing(data.swing_b, 'camera2', metric)
    // Normalize to 0..100% index for overlay
    const n = Math.max(sa.length, sb.length, 1)
    const norm = (arr: Array<number | null>) => {
      if (arr.length === 0) return Array.from({ length: n }, () => null)
      return Array.from({ length: n }, (_, i) => {
        const src = Math.round((i / Math.max(n - 1, 1)) * (arr.length - 1))
        return arr[src] ?? null
      })
    }
    return [
      { label: `A · ${a}`, color: '#58a6ff', values: norm(sa) },
      { label: `B · ${b}`, color: '#3fb950', values: norm(sb), dashed: true },
    ]
  }, [data, metric, a, b])

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <h2>Compare Swings</h2>
        <p>Pick two saved analyses. Reference swing is preferred as A when set.</p>
      </header>

      <div className={styles.pickers}>
        <label>
          Swing A
          <select value={a} onChange={(e) => setA(e.target.value)}>
            {analyses.map((item) => (
              <option key={item.timestamp} value={item.timestamp}>
                {item.date}
                {item.is_reference ? ' · REF' : ''}
              </option>
            ))}
          </select>
        </label>
        <label>
          Swing B
          <select value={b} onChange={(e) => setB(e.target.value)}>
            {analyses.map((item) => (
              <option key={item.timestamp} value={item.timestamp}>
                {item.date}
                {item.is_reference ? ' · REF' : ''}
              </option>
            ))}
          </select>
        </label>
        <button type="button" disabled={loading || !a || !b} onClick={() => void runCompare()}>
          {loading ? 'Comparing…' : 'Refresh'}
        </button>
      </div>

      {error && <p className={styles.error}>{error}</p>}
      {!analyses.length && <p className={styles.empty}>No saved analyses yet — record and analyze first.</p>}

      {data && (
        <>
          <div className={styles.deltas}>
            <DeltaCard title="Camera 1 (Face-On)" deltas={data.deltas.camera1} keys={CAM1_KEYS} />
            <DeltaCard title="Camera 2 (DTL)" deltas={data.deltas.camera2} keys={CAM2_KEYS} />
          </div>

          <div className={styles.chartBlock}>
            <div className={styles.chartHead}>
              <h3>Overlay (normalized timeline)</h3>
              <select value={metric} onChange={(e) => setMetric(e.target.value)}>
                <option value="shoulder_turn">Shoulder turn</option>
                <option value="hip_turn">Hip turn</option>
                <option value="x_factor">X-factor</option>
                <option value="sway">Sway</option>
              </select>
            </div>
            <LineChart series={chartSeries} yLabel={metric.replace(/_/g, ' ')} />
          </div>
        </>
      )}
    </section>
  )
}

function DeltaCard({
  title,
  deltas,
  keys,
}: {
  title: string
  deltas: Record<string, CompareDelta> | null
  keys: string[]
}) {
  if (!deltas) {
    return (
      <div className={styles.card}>
        <h3>{title}</h3>
        <p className={styles.empty}>No summary data</p>
      </div>
    )
  }
  return (
    <div className={styles.card}>
      <h3>{title}</h3>
      <div className={styles.deltaGrid}>
        {keys.map((k) => {
          const d = deltas[k]
          if (!d) return null
          const delta = d.delta
          const cls =
            delta == null ? '' : delta > 0 ? styles.up : delta < 0 ? styles.down : styles.flat
          return (
            <div key={k} className={styles.deltaItem}>
              <span>{k.replace(/_/g, ' ')}</span>
              <strong>
                {fmt(d.a)} → {fmt(d.b)}
              </strong>
              <em className={cls}>
                {delta == null ? '—' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}`}
              </em>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function fmt(v: number | null | undefined) {
  return v == null ? '—' : Number(v).toFixed(1)
}
