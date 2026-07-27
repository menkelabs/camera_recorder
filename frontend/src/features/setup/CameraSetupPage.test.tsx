import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import { mockStatus } from '../../test/mockStatus'
import { CameraSetupPage } from './CameraSetupPage'

vi.mock('../../components/CameraPreview', () => ({
  CameraPreview: ({ label }: { label: string }) => <div>{label}</div>,
}))
vi.mock('../../components/PropertySliders', () => ({
  PropertySliders: () => <div>sliders</div>,
}))

describe('CameraSetupPage', () => {
  beforeEach(() => {
    useAppStore.setState({
      tab: 'camera1',
      status: mockStatus(),
      statusError: null,
      streamSession: 2,
    })
  })

  it('detects and reinits cameras', async () => {
    const detect = vi.spyOn(api, 'detectCameras').mockResolvedValue({
      available_indices: [0, 1],
      camera1_id: 0,
      camera2_id: 1,
      camera1_available: true,
      camera2_available: true,
    })
    const reinit = vi.spyOn(api, 'reinitCameras').mockResolvedValue({
      cameras_available: true,
    })

    render(<CameraSetupPage cameraNum={1} />)
    expect(screen.getByText(/Camera 1 \(Face-On\)/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Detect/i }))
    await waitFor(() => expect(detect).toHaveBeenCalled())

    await userEvent.click(screen.getByRole('button', { name: /Re-?init/i }))
    await waitFor(() => expect(reinit).toHaveBeenCalled())
  })
})