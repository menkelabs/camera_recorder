/**
 * Serialized analysis frame seek — prevents the v1 setInterval storm where
 * each tick fired overlapping POST/GET requests.
 */

export type SeekFn = (index: number) => Promise<void>

export class PlaybackSequencer {
  private inFlight = false
  private pending: number | null = null
  private current = 0
  private disposed = false
  private seek: SeekFn
  private onIndex?: (index: number) => void

  constructor(seek: SeekFn, onIndex?: (index: number) => void) {
    this.seek = seek
    this.onIndex = onIndex
  }

  get index() {
    return this.current
  }

  /** Request a frame; coalesces to the latest index while a seek is in flight. */
  request(index: number) {
    if (this.disposed) return
    const next = Math.max(0, Math.floor(index))
    if (this.inFlight) {
      this.pending = next
      return
    }
    void this.run(next)
  }

  private async run(index: number) {
    this.inFlight = true
    this.current = index
    this.onIndex?.(index)
    try {
      await this.seek(index)
    } finally {
      this.inFlight = false
      if (this.disposed) return
      if (this.pending !== null) {
        const p = this.pending
        this.pending = null
        void this.run(p)
      }
    }
  }

  dispose() {
    this.disposed = true
    this.pending = null
  }
}

export function playIntervalMs(speed: number, baseFps = 15): number {
  const s = Math.max(0.01, speed)
  return Math.round(1000 / (baseFps * s))
}
