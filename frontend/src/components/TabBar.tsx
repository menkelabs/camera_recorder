import { TABS, useAppStore } from '../store/appStore'
import styles from './TabBar.module.css'

export function TabBar() {
  const tab = useAppStore((s) => s.tab)
  const setTab = useAppStore((s) => s.setTab)

  return (
    <nav className={styles.bar} role="tablist" aria-label="Main">
      {TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={tab === t.id}
          className={tab === t.id ? styles.active : undefined}
          onClick={() => setTab(t.id)}
        >
          <span className={styles.key}>{t.shortcut}</span>
          {t.label}
        </button>
      ))}
    </nav>
  )
}
