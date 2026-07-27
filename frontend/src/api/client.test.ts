import { describe, expect, it } from 'vitest'
import { formatPropValue } from './client'

describe('formatPropValue', () => {
  it('formats exposure and white balance specially', () => {
    expect(formatPropValue('exposure', -6.25)).toBe('-6.3')
    expect(formatPropValue('white_balance', 4000.2)).toBe('4000K')
    expect(formatPropValue('brightness', 128.4)).toBe('128')
  })
})
