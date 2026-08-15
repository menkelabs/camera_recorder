import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import AnalysisPlayback from './AnalysisPlayback.vue'

describe('AnalysisPlayback', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'setAnalysisFrame').mockResolvedValue({
      max_frames: 5,
      frame_index: 0,
      is_analyzing: false,
      has_frames: true,
      camera1: null,
      camera2: null,
    })
  })

  it('steps frames with keyboard shortcuts', async () => {
    render(AnalysisPlayback, { props: { maxFrames: 5, initialIndex: 0 } })
    expect(await screen.findByText('1 / 5')).toBeTruthy()

    await userEvent.keyboard('{ArrowRight}')
    expect(api.setAnalysisFrame).toHaveBeenCalledWith(1)

    await userEvent.keyboard(' ')
    expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
  })
})
