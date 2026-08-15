import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import { mockStatus } from '../../test/mockStatus'
import CameraSetupPage from './CameraSetupPage.vue'

vi.mock('../../components/CameraPreview.vue', () => ({
  default: {
    props: ['label'],
    template: '<div>{{ label }}</div>',
  },
}))
vi.mock('../../components/PropertySliders.vue', () => ({
  default: { template: '<div>sliders</div>' },
}))

function mountPage(overrides = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAppStore().$patch({
    status: mockStatus(overrides),
    streamSession: 2,
  })
  return render(CameraSetupPage, {
    props: { cameraNum: 1 },
    global: { plugins: [pinia] },
  })
}

describe('CameraSetupPage', () => {
  beforeEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('shows an offline banner when cameras are unavailable', async () => {
    mountPage({ cameras_available: false })
    expect(await screen.findByText(/Cameras offline/)).toBeTruthy()
  })

  it('detect and reinit bump the stream session', async () => {
    const detect = vi.spyOn(api, 'detectCameras').mockResolvedValue({
      available_indices: [0, 2],
      camera1_id: 0,
      camera2_id: 2,
      camera1_available: true,
      camera2_available: true,
    })
    const reinit = vi.spyOn(api, 'reinitCameras').mockResolvedValue({ success: true })
    mountPage()
    expect(screen.queryByText(/Cameras offline/)).toBeNull()

    await userEvent.click(screen.getByRole('button', { name: 'Detect' }))
    await waitFor(() => expect(detect).toHaveBeenCalled())
    expect(useAppStore().streamSession).toBe(3)

    await userEvent.click(screen.getByRole('button', { name: 'Reinit' }))
    await waitFor(() => expect(reinit).toHaveBeenCalled())
    expect(useAppStore().streamSession).toBe(4)
  })
})
