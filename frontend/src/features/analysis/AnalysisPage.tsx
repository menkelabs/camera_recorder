import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { AnalysisResults, AnalysisScore } from '../../api/types'
import { AnalysisPlayback } from './AnalysisPlayback'
import styles from './AnalysisPage.module.css'

export function AnalysisPage() {
  const [results, setResults] = useState<AnalysisResults | null>(null)
  const [score, setScore] = useState<AnalysisScore | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [exportMsg, setExportMsg] = useState<string | null>(null)
  const [exportBusy, setExportBusy] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const data = await api.analysisResults()
      setResults(data)
      setError(null)
      if (!data.is_analyzing && data.max_frames > 0) {
        try {
          setScore(await api.analysisScore())
        } catch {
          setScore(null)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis')
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!results?.is_analyzing) return
    const id = setInterval(() => void refresh(), 1000)
    return () => clearInterval(id)
  }, [refresh, results?.is_analyzing])

  const cam1 = results?.camera1
  const phase = cam1?.current?.phase
  const hasFrames = Boolean(results && results.max_frames > 0 && !results.is_analyzing)

  const downloadReport = (format: 'html' | 'csv') => {
    setExportMsg(null)
    window.location.assign(api.analysisExportUrl(format))
  }

  const downloadClip = async (camera: 1 | 2) => {
    setExportBusy(true)
    setExportMsg(null)
    try {
      const data = await api.exportClip(camera, 30)
      if (data.error || !data.filename) {
        setExportMsg(data.error || 'Clip export failed')
        return
      }
      window.location.assign(api.analysisClipUrl(data.filename))
      setExportMsg(`Saved ${data.filename}`)
    } catch (err) {
      setExportMsg(err instanceof Error ? err.message : 'Clip export failed')
    } finally {
      setExportBusy(false)
    }
  }

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2>Analysis</h2>
          {phase != null && <span className={styles.phase}>{String(phase)}</span>}
        </div>
        <div className={styles.headerRight}>
          {score?.score != null && (
            <div className={styles.score}>
              <span className={styles.grade}>{score.grade || '—'}</span>
              <span className={styles.scoreNum}>{Math.round(Number(score.score))}</span>
            </div>
          )}
          {hasFrames && (
            <div className={styles.exportActions} role="group" aria-label="Export analysis">
              <button type="button" onClick={() => downloadReport('html')}>
                Export HTML
              </button>
              <button type="button" onClick={() => downloadReport('csv')}>
                Export CSV
              </button>
              <button
                type="button"
                disabled={exportBusy}
                onClick={() => void downloadClip(1)}
              >
                Clip Cam1
              </button>
              <button
                type="button"
                disabled={exportBusy}
                onClick={() => void downloadClip(2)}
              >
                Clip Cam2
              </button>
            </div>
          )}
        </div>
      </header>
      {exportMsg && <p className={styles.exportMsg}>{exportMsg}</p>}

      {results?.is_analyzing && (
        <p className={styles.progress}>{results.progress || 'Analyzing…'}</p>
      )}
      {(error || results?.analysis_error) && (
        <p className={styles.error}>{error || results?.analysis_error}</p>
      )}

      <AnalysisPlayback
        maxFrames={results?.max_frames || 0}
        initialIndex={results?.frame_index || 0}
        onResults={(data) => setResults(data as AnalysisResults)}
      />

      {(cam1 || results?.camera2) && (
        <div className={styles.metrics}>
          <MetricBlock
            title="Camera 1"
            detection={cam1?.detection_rate}
            current={cam1?.current}
            keys={['sway', 'head_sway', 'spine_tilt', 'knee_flex', 'weight_shift']}
          />
          <MetricBlock
            title="Camera 2"
            detection={results?.camera2?.detection_rate}
            current={results?.camera2?.current}
            keys={['shoulder_turn', 'hip_turn', 'x_factor', 'spine_angle', 'lead_arm_angle']}
          />
        </div>
      )}

      {score && (score.focus?.length || score.strengths?.length) ? (
        <div className={styles.coach}>
          {!!score.strengths?.length && (
            <div>
              <h4>Strengths</h4>
              <ul>
                {score.strengths.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {!!score.focus?.length && (
            <div>
              <h4>Focus</h4>
              <ul>
                {score.focus.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : null}
    </section>
  )
}

function MetricBlock({
  title,
  detection,
  current,
  keys,
}: {
  title: string
  detection?: number
  current?: Record<string, number | string | null | undefined>
  keys: string[]
}) {
  if (!current) {
    return (
      <div className={styles.block}>
        <h3>{title}</h3>
        <p className={styles.muted}>No data</p>
      </div>
    )
  }
  return (
    <div className={styles.block}>
      <h3>
        {title}
        {detection != null && (
          <span className={styles.det}>{detection.toFixed(0)}% det</span>
        )}
      </h3>
      <div className={styles.grid}>
        {keys.map((k) => (
          <div key={k} className={styles.metric}>
            <span>{k.replace(/_/g, ' ')}</span>
            <strong>
              {current[k] == null || current[k] === ''
                ? '—'
                : typeof current[k] === 'number'
                  ? Number(current[k]).toFixed(1)
                  : String(current[k])}
            </strong>
          </div>
        ))}
      </div>
    </div>
  )
}
