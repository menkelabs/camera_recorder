import { describe, expect, it } from 'vitest'
import { frameIndexForPhase, phaseNameAt, videoTimeForPhase } from './phaseSync'

const swingA = [
  'Address',
  'Address',
  'Backswing',
  'Top',
  'Top',
  'Downswing',
  'Impact',
  'Follow-through',
]
const swingB = [
  'Address',
  'Backswing',
  'Backswing',
  'Backswing',
  'Top',
  'Downswing',
  'Downswing',
  'Impact',
  'Follow-through',
  'Follow-through',
]

describe('phaseSync', () => {
  it('lands both swings on the same phase at the same playhead', () => {
    const intoTop = 2 / 6 + 0.01
    expect(phaseNameAt(swingA, intoTop)).toBe('Top')
    expect(phaseNameAt(swingB, intoTop)).toBe('Top')
    expect(phaseNameAt(swingA, 0)).toBe('Address')
    expect(phaseNameAt(swingB, 0)).toBe('Address')
    expect(phaseNameAt(swingA, 0.99)).toBe('Follow-through')
    expect(phaseNameAt(swingB, 0.99)).toBe('Follow-through')
  })

  it('maps a sampled frame index back onto the source video clock', () => {
    const index = frameIndexForPhase(swingA, 0)
    expect(videoTimeForPhase(swingA, 0, 4, 4, 120)).toBe((index * 4) / 120)
  })
})