import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import { mockStatus } from '../../test/mockStatus'
import { RecordingPage } from './RecordingPage'

vi.mock('../../components/CameraPreview', () => ({
  CameraPreview: ({ label }: { label: string }) => <div>{label}</div>,
}))
vi.mock('./PracticeTools', () => ({
  PracticeTools: () => <div>Practice tools</div>,
}))

describe('RecordingPage', () => {
  beforeEach(() => {
    useAppStore.setState({
      tab: 'recording',
      status: mockStatus(),
      statusError: null,
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
    render(<RecordingPage />)

    expect(await screen.findByText(/Camera 1 \(Face-On\)/)).toBeInTheDocument()
    expect(screen.getByText(/Camera 2 \(Down-the-Line\)/)).toBeInTheDocument()
    expect(await screen.findByText('Camera 1 open')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Start recording' }))
    await waitFor(() => expect(start).toHaveBeenCalled())
  })

  it('surfaces checklist errors from startRecording', async () => {
    vi.spyOn(api, 'startRecording').mockResolvedValue({
      error: 'Checklist failed: Camera 1 delivering frames',
      checklist: {
        ready: false,
        items: [
          {
            id: 'frames1',
            label: 'Camera 1 delivering frames',
            ok: false,
            detail: 'No recent frames',
            required: true,
          },
        ],
      },
    })
    render(<RecordingPage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Start recording' }))
    expect(await screen.findByText(/Checklist failed/)).toBeInTheDocument()
  })
})
