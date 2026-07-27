import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { AnalysisResults } from '../../api/types'
import { AnalysisPlayback } from './AnalysisPlayback'
import styles from './AnalysisPage.module.css'

export function AnalysisPage() {
  const [results, setResults] = useState<AnalysisResults | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await api.analysisResults()
      setResults(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis')
    }
  }, [])

  useEffect(() => {
    void refresh()
    const id = setInterval(() => {
      if (results?.is_analyzing) void refresh()
    }, 1000)
    return () => clearInterval(id)
  }, [refresh, results?.is_analyzing])

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <h2>Analysis</h2>
        {results?.is_analyzing && (
          <span className={styles.progress}>{results.progress || 'Analyzing…'}</span>
        )}
        {(error || results?.analysis_error) && (
          <p className={styles.error}>{error || results?.analysis_error}</p>
        )}
      </header>
      <AnalysisPlayback
        maxFrames={results?.max_frames || 0}
        initialIndex={results?.frame_index || 0}
        onResults={(data) => setResults(data as AnalysisResults)}
      />
    </section>
  )
}
