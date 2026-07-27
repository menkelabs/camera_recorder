import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import CameraPreview from './CameraPreview.vue'

describe('CameraPreview', () => {
  it('sets video_feed src only while active', async () => {
    const { rerender } = render(CameraPreview, {
      props: { cameraNum: 1, active: true, session: 3, label: 'Cam 1' },
    })
    const img = screen.getByAltText('Cam 1') as HTMLImageElement
    expect(img.getAttribute('src')).toContain('/video_feed/1?s=3')

    await rerender({ cameraNum: 1, active: false, session: 3, label: 'Cam 1' })
    expect(screen.getByText('Feed paused')).toBeTruthy()
    expect(screen.queryByAltText('Cam 1')).toBeNull()
  })

  it('shows REC badge while recording and active', () => {
    render(CameraPreview, {
      props: { cameraNum: 2, active: true, recording: true, label: 'Cam 2' },
    })
    expect(screen.getByText('REC')).toBeTruthy()
  })
})
