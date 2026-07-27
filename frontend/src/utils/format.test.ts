import { describe, expect, it } from 'vitest'
import { formatBytes, formatDuration } from './format'

describe('formatBytes', () => {
  it('formats common sizes', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2.00 KB')
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.00 MB')
  })
})

describe('formatDuration', () => {
  it('formats seconds and minutes', () => {
    expect(formatDuration(null)).toBe('—')
    expect(formatDuration(12.34)).toBe('12.3s')
    expect(formatDuration(75)).toBe('1m 15s')
  })
})
