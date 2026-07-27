import type { ChecklistResponse } from '../../api/types'
import styles from './ChecklistPanel.module.css'

interface Props {
  checklist: ChecklistResponse | null
}

export function ChecklistPanel({ checklist }: Props) {
  if (!checklist) {
    return (
      <div className={styles.panel}>
        <h3>Pre-Record Checklist</h3>
        <p className={styles.muted}>Checking cameras…</p>
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <h3>Pre-Record Checklist</h3>
        <span className={checklist.ready ? styles.ready : styles.notReady}>
          {checklist.ready ? 'Ready' : 'Not Ready'}
        </span>
      </div>
      <ul className={styles.list}>
        {(checklist.items || []).map((item) => {
          const cls = item.ok ? styles.ok : item.required ? styles.bad : styles.warn
          return (
            <li key={item.id} className={cls}>
              <span className={styles.mark}>{item.ok ? '✓' : '✗'}</span>
              <span>
                <strong>{item.label}</strong> — {item.detail}
              </span>
            </li>
          )
        })}
      </ul>
      {checklist.usb_warning && (
        <p className={styles.usb}>{checklist.usb_warning}</p>
      )}
    </div>
  )
}
