import { describe, expect, it } from 'vitest'
import { api, formatPropValue } from './client'

describe('formatPropValue', () => {
  it('formats exposure and white balance specially', () => {
    expect(formatPropValue('exposure', -6.25)).toBe('-6.3')
    expect(formatPropValue('white_balance', 4000.2)).toBe('4000K')
    expect(formatPropValue('brightness', 128.4)).toBe('128')
  })
})

describe('analysis export helpers', () => {
  it('builds export and clip URLs', () => {
    expect(api.analysisExportUrl('html')).toBe('/api/analysis/export?format=html')
    expect(api.analysisExportUrl('csv', '20260715_120000')).toBe(
      '/api/analysis/export?format=csv&timestamp=20260715_120000',
    )
    expect(api.analysisClipUrl('clip_20260715_120000_camera1.mp4')).toBe(
      '/api/analysis/clip/clip_20260715_120000_camera1.mp4',
    )
  })
})
