import { render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import AnalysisPage from './AnalysisPage.vue'

vi.mock('./AnalysisPlayback.vue', () => ({
  default: { template: '<div data-testid="playback">playback</div>' },
}))

describe('AnalysisPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
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

    render(AnalysisPage)
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
})
