import { describe, expect, it, vi } from 'vitest'
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

describe('API query helpers', () => {
  it('includes optional timestamp and scope on score/list URLs', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ recordings: [], count: 0, total_size: 0 }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await api.analysisScore('20260715_120000')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/analysis/score?timestamp=20260715_120000',
      expect.any(Object),
    )

    await api.analysisResults('20260715_120000')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/analysis/results?timestamp=20260715_120000',
      expect.any(Object),
    )

    await api.listRecordings({ scope: 'unclaimed' })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/recordings?scope=unclaimed',
      expect.any(Object),
    )

    vi.unstubAllGlobals()
  })

  it('rejects HTTP errors and 200 payloads that still carry error', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        statusText: 'Conflict',
        json: async () => ({ error: 'Already recording' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        statusText: 'OK',
        json: async () => ({ error: 'Cameras not available' }),
      })
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.startRecording()).rejects.toThrow('Already recording')
    await expect(api.startRecording()).rejects.toThrow('Cameras not available')

    vi.unstubAllGlobals()
  })
})
