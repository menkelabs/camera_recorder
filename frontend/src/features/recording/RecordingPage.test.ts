import { render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import { mockStatus } from '../../test/mockStatus'
import RecordingPage from './RecordingPage.vue'

vi.mock('../../components/CameraPreview.vue', () => ({
  default: {
    props: ['label'],
    template: '<div>{{ label }}</div>',
  },
}))
vi.mock('./PracticeTools.vue', () => ({
  default: { template: '<div>Practice tools</div>' },
}))

describe('RecordingPage', () => {
  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
    useAppStore().$patch({
      tab: 'recording',
      status: mockStatus(),
      streamSession: 1,
    })
    vi.spyOn(api, 'checklist').mockResolvedValue({
      ready: true,
      items: [
        { id: 'camera1', label: 'Camera 1 open', ok: true, detail: 'OK', required: true },
        { id: 'camera2', label: 'Camera 2 open', ok: true, detail: 'OK', required: true },
      ],
    })
  })

  it('shows dual previews, checklist, and starts recording', async () => {
    const start = vi.spyOn(api, 'startRecording').mockResolvedValue({ success: true })
    const pinia = createPinia()
    setActivePinia(pinia)
    useAppStore().$patch({ status: mockStatus(), streamSession: 1 })
    render(RecordingPage, { global: { plugins: [pinia] } })

    expect(await screen.findByText(/Camera 1 \(Face-On\)/)).toBeTruthy()
    expect(screen.getByText(/Camera 2 \(Down-the-Line\)/)).toBeTruthy()
    expect(await screen.findByText(/Camera 1 open/)).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: 'Start recording' }))
    await waitFor(() => expect(start).toHaveBeenCalled())
  })
})
