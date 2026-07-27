import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { AnalysisPage } from './AnalysisPage'

vi.mock('./AnalysisPlayback', () => ({
  AnalysisPlayback: () => <div data-testid="playback">playback</div>,
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
      },
      camera2: {
        detection_rate: 88,
        current: { shoulder_turn: 40 },
      },
    } as never)
    vi.spyOn(api, 'analysisScore').mockResolvedValue({
      score: 82,
      grade: 'B',
      strengths: ['Tempo'],
      focus: ['Sway'],
    } as never)

    const assign = vi.fn()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, assign },
    })

    render(<AnalysisPage />)

    expect(await screen.findByRole('heading', { name: 'Analysis' })).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText('Top')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Export HTML' }))
    expect(assign).toHaveBeenCalledWith('/api/analysis/export?format=html')

    await userEvent.click(screen.getByRole('button', { name: 'Export CSV' }))
    expect(assign).toHaveBeenCalledWith('/api/analysis/export?format=csv')

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

  it('hides export actions while analyzing or empty', async () => {
    vi.spyOn(api, 'analysisResults').mockResolvedValue({
      max_frames: 0,
      frame_index: 0,
      is_analyzing: true,
      progress: 'Processing Camera 1...',
      has_frames: false,
    } as never)

    render(<AnalysisPage />)
    expect(await screen.findByText(/Processing Camera 1/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Export HTML' })).toBeNull()
  })
})
