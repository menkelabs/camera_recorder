import { useEffect, useMemo, useRef, useState } from 'react'
import { api, formatPropValue } from '../api/client'
import type { CameraProperties } from '../api/types'
import { PROP_ORDER } from '../api/types'
import styles from './PropertySliders.module.css'

interface Props {
  cameraNum: 1 | 2
  active: boolean
}

export function PropertySliders({ cameraNum, active }: Props) {
  const [props, setProps] = useState<CameraProperties | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [local, setLocal] = useState<Record<string, number>>({})
  const debounce = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  const refresh = async () => {
    try {
      const data = await api.cameraProperties(cameraNum)
      if (data.error) {
        setError(data.error)
        setProps(null)
        return
      }
      setError(null)
      setProps(data)
      const next: Record<string, number> = {}
      for (const name of PROP_ORDER) {
        const p = data[name]
        if (p) next[name] = p.value
      }
      setLocal(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load properties')
    }
  }

  useEffect(() => {
    if (!active) return
    void refresh()
    const id = setInterval(() => void refresh(), 2000)
    return () => clearInterval(id)
  }, [active, cameraNum])

  const info = props?._info

  const rows = useMemo(() => {
    if (!props) return []
    return PROP_ORDER.filter((name) => props[name]).map((name) => ({
      name,
      ...props[name],
      value: local[name] ?? props[name].value,
    }))
  }, [props, local])

  const onChange = (name: string, value: number) => {
    setLocal((prev) => ({ ...prev, [name]: value }))
    clearTimeout(debounce.current[name])
    debounce.current[name] = setTimeout(() => {
      void api.setCameraProperty(cameraNum, name, value).catch(() => {})
    }, 50)
  }

  if (error) {
    return <div className={styles.error}>{error}</div>
  }

  if (!props) {
    return <div className={styles.loading}>Loading properties…</div>
  }

  return (
    <div className={styles.wrap}>
      {info && (
        <p className={styles.info}>
          {info.width}×{info.height} @ {Number(info.fps || 0).toFixed(1)} fps
        </p>
      )}
      <div className={styles.list}>
        {rows.map((row) => (
          <label key={row.name} className={styles.row}>
            <span className={styles.label}>{row.name.replace('_', ' ')}</span>
            <input
              type="range"
              min={row.min}
              max={row.max}
              step={row.step}
              value={row.value}
              onChange={(e) => onChange(row.name, Number(e.target.value))}
            />
            <span className={styles.value}>{formatPropValue(row.name, row.value)}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
