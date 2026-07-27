import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { useMetronome } from '../../hooks/useMetronome'
import { useAppStore } from '../../store/appStore'
import styles from './PracticeTools.module.css'

export function PracticeTools() {
  const status = useAppStore((s) => s.status)
  const setTab = useAppStore((s) => s.setTab)
  const session = status?.session
  const [bpm, setBpm] = useState(60)
  const [metroOn, setMetroOn] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const { beatAccent, pulse } = useMetronome(bpm, metroOn)

  useEffect(() => {
    const metro = status?.practice?.metronome
    if (!metro) return
    setBpm(metro.bpm || 60)
    // Don't auto-start audio from server settings (needs user gesture)
  }, [status?.practice?.metronome?.bpm])

  const persistMetro = async (enabled: boolean, nextBpm: number) => {
    try {
      await api.updatePracticeSettings({
        metronome: { enabled, bpm: nextBpm, ratio: '3:1' },
      })
    } catch {
      /* ignore */
    }
  }

  const toggleSession = async (enabled: boolean) => {
    setMessage(null)
    try {
      const res = await api.setSessionEnabled(enabled)
      if (res.error) setMessage(res.error)
      else if (enabled) setTab('recording')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Session toggle failed')
    }
  }

  const nextSwing = async () => {
    setMessage(null)
    try {
      const res = await api.sessionNext()
      if (res.error) setMessage(res.error)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Next swing failed')
    }
  }

  return (
    <div className={styles.panel}>
      <h3>Practice Tools</h3>
      <div className={styles.row}>
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={Boolean(session?.enabled)}
            onChange={(e) => void toggleSession(e.target.checked)}
          />
          Session mode
        </label>
        <span className={styles.meta}>{session?.phase || 'idle'}</span>
        <span className={styles.meta}>swings: {session?.count ?? 0}</span>
        {session?.enabled && session.phase === 'review' && (
          <button type="button" onClick={() => void nextSwing()}>
            Next swing
          </button>
        )}
      </div>
      <div className={styles.row}>
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={metroOn}
            onChange={(e) => {
              const on = e.target.checked
              setMetroOn(on)
              void persistMetro(on, bpm)
            }}
          />
          Tempo metronome
        </label>
        <span
          key={pulse}
          className={`${styles.beat} ${metroOn ? (beatAccent ? styles.accent : styles.pulse) : ''}`}
        />
        <label className={styles.bpm}>
          BPM
          <input
            type="number"
            min={40}
            max={120}
            value={bpm}
            onChange={(e) => {
              const v = Math.min(120, Math.max(40, Number(e.target.value) || 60))
              setBpm(v)
              void persistMetro(metroOn, v)
            }}
          />
        </label>
        <span className={styles.meta}>3:1 feel</span>
      </div>
      {message && <p className={styles.error}>{message}</p>}
    </div>
  )
}
