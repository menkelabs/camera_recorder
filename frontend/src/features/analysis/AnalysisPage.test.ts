import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import AnalysisPage from './AnalysisPage.vue'

vi.mock('./AnalysisPlayback.vue', () => ({
  default: { template: '<div data-testid="playback">playback</div>' },
}))

function mountPage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return render(AnalysisPage, { global: { plugins: [pinia] } })
}

describe('AnalysisPage', () => {
  beforeEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.spyOn(api, 'listAnalyses').mockResolvedValue({ analyses: [], count: 0 })
    vi.spyOn(api, 'analysisScore').mockResolvedValue({
      score: 82,
      grade: 'B',
      strengths: [],
      focus_areas: [],
    })
  })

  it('renders export and clip actions when analysis has frames', async () => {
    vi.spyOn(api, 'analysisResults').mockResolvedValue({
      max_frames: 12,
      frame_index: 0,
      is_analyzing: false,
      has_frames: true,
      camera1: {
        detection_rate: 90,
        current: { phase: 'Top', sway: -4 },
        summary: {},
        timeseries: {},
      },
      camera2: {
        detection_rate: 88,
        current: { shoulder_turn: 40 },
        summary: {},
        timeseries: {},
      },
    } as never)
    vi.spyOn(api, 'analysisScore').mockResolvedValue({
      score: 82,
      grade: 'B',
      strengths: ['Tempo'],
      focus_areas: ['Lateral Sway'],
    } as never)

    const assign = vi.fn()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, assign },
    })

    mountPage()
    expect(await screen.findByRole('button', { name: 'Export HTML' })).toBeTruthy()
    expect(await screen.findByText('B')).toBeTruthy()
    expect(await screen.findByText('Lateral Sway')).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: 'Export HTML' }))
    expect(assign).toHaveBeenCalledWith('/api/analysis/export?format=html')

    vi.spyOn(api, 'exportClip').mockResolvedValue({
      success: true,
      filename: 'clip_20260727_120000_camera1.mp4',
      frame_count: 12,
    })
    await userEvent.click(screen.getByRole('button', { name: 'Clip Cam1' }))
    await waitFor(() =>
      expect(assign).toHaveBeenCalledWith(
        '/api/analysis/clip/clip_20260727_120000_camera1.mp4',
      ),
    )
  })

  it('loads a saved swing from the history picker', async () => {
    vi.mocked(api.listAnalyses).mockResolvedValue({
      analyses: [{ timestamp: '20260715_120000', date: '2026-07-15 12:00', is_reference: true }],
      count: 1,
    })
    const live = vi.spyOn(api, 'analysisResults').mockResolvedValue({
      max_frames: 0,
      frame_index: 0,
      is_analyzing: false,
      has_frames: false,
      camera1: null,
      camera2: null,
      source: 'live',
    })
    vi.spyOn(api, 'analysisScore').mockResolvedValue({
      score: 91,
      grade: 'A',
      strengths: ['Tempo'],
      focus_areas: [],
    })

    mountPage()
    expect(await screen.findByRole('option', { name: /2026-07-15/ })).toBeTruthy()
    live.mockResolvedValue({
      max_frames: 8,
      frame_index: 0,
      is_analyzing: false,
      has_frames: false,
      source: 'saved',
      timestamp: '20260715_120000',
      camera1: {
        detection_rate: 90,
        current: { phase: 'Impact', sway: 2 },
        summary: {},
        timeseries: {},
      },
      camera2: {
        detection_rate: 88,
        current: { shoulder_turn: 70 },
        summary: {},
        timeseries: {},
      },
      score: { score: 91, grade: 'A', strengths: ['Tempo'], focus_areas: [] },
    } as never)

    await userEvent.selectOptions(screen.getByRole('combobox'), '20260715_120000')
    expect(await screen.findByText(/Saved swing/)).toBeTruthy()
    expect(screen.getByText('A')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Export HTML' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Clip Cam1' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Clip Cam2' })).toBeTruthy()
  })

  it('uses analysisPrefill from the store', async () => {
    vi.spyOn(api, 'listAnalyses').mockResolvedValue({
      analyses: [{ timestamp: '20260716_120000', date: '2026-07-16 12:00' }],
      count: 1,
    })
    const results = vi.spyOn(api, 'analysisResults').mockResolvedValue({
      max_frames: 4,
      frame_index: 0,
      is_analyzing: false,
      has_frames: false,
      source: 'saved',
      timestamp: '20260716_120000',
      camera1: {
        detection_rate: 80,
        current: { sway: 1 },
        summary: {},
        timeseries: {},
      },
      camera2: null,
    } as never)

    const pinia = createPinia()
    setActivePinia(pinia)
    useAppStore().setAnalysisPrefill('20260716_120000')
    render(AnalysisPage, { global: { plugins: [pinia] } })
    await waitFor(() => expect(results).toHaveBeenCalledWith('20260716_120000'))
    expect(useAppStore().analysisPrefill).toBeNull()
  })
})
