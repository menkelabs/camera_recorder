import { describe, expect, it, vi } from 'vitest'
import { PlaybackSequencer, playIntervalMs } from './playbackSequencer'

describe('PlaybackSequencer', () => {
  it('runs seeks serially and coalesces to the latest pending index', async () => {
    const order: number[] = []
    let release!: () => void
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })

    const seek = vi.fn(async (index: number) => {
      order.push(index)
      if (index === 1) await gate
    })

    const seq = new PlaybackSequencer(seek)
    seq.request(1)
    // Allow first seek to start
    await Promise.resolve()
    seq.request(2)
    seq.request(5)
    expect(seek).toHaveBeenCalledTimes(1)

    release()
    await vi.waitFor(() => expect(seek).toHaveBeenCalledTimes(2))
    expect(order).toEqual([1, 5])
    seq.dispose()
  })

  it('computes play interval from speed', () => {
    expect(playIntervalMs(1, 15)).toBe(Math.round(1000 / 15))
    expect(playIntervalMs(2, 15)).toBe(Math.round(1000 / 30))
  })
})
