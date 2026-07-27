import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CameraPreview } from './CameraPreview'

describe('CameraPreview', () => {
  it('sets video_feed src only while active', () => {
    const { rerender } = render(
      <CameraPreview cameraNum={1} active session={3} label="Cam 1" />,
    )
    const img = screen.getByAltText('Cam 1') as HTMLImageElement
    expect(img.getAttribute('src')).toContain('/video_feed/1?s=3')

    rerender(<CameraPreview cameraNum={1} active={false} session={3} label="Cam 1" />)
    expect(screen.getByText('Feed paused')).toBeInTheDocument()
    expect(screen.queryByAltText('Cam 1')).toBeNull()
  })

  it('shows REC badge while recording and active', () => {
    render(
      <CameraPreview cameraNum={2} active recording label="Cam 2" />,
    )
    expect(screen.getByText('REC')).toBeInTheDocument()
  })
})
