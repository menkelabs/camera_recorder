import styles from './PlaceholderPage.module.css'

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <section className={styles.page}>
      <h2>{title}</h2>
      <p>Ported in Phase C feature parity. API remains available under <code>/api/*</code>.</p>
      <p>
        Meanwhile use <a href="/legacy">/legacy</a> for the full v1 UI.
      </p>
    </section>
  )
}
