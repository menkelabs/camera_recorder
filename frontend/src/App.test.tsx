import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { api } from './api/client'
import { useAppStore } from './store/appStore'
import { mockStatus } from './test/mockStatus'

vi.mock('./hooks/useStatusPoll', () => ({
  useStatusPoll: () => undefined,
}))

vi.mock('./features/setup/CameraSetupPage', () => ({
  CameraSetupPage: ({ cameraNum }: { cameraNum: number }) => (
    <div>Setup cam {cameraNum}</div>
  ),
}))
vi.mock('./features/recording/RecordingPage', () => ({
  RecordingPage: () => <div>Recording page</div>,
}))
vi.mock('./features/recordings/RecordingsPage', () => ({
  RecordingsPage: () => <div>Recordings page</div>,
}))
vi.mock('./features/analysis/AnalysisPage', () => ({
  AnalysisPage: () => <div>Analysis page</div>,
}))
vi.mock('./features/compare/ComparePage', () => ({
  ComparePage: () => <div>Compare page</div>,
}))
vi.mock('./features/progress/ProgressPage', () => ({
  ProgressPage: () => <div>Progress page</div>,
}))
vi.mock('./features/settings/SettingsPage', () => ({
  SettingsPage: () => <div>Settings page</div>,
}))

describe('App shell', () => {
  beforeEach(() => {
    useAppStore.setState({
      tab: 'recording',
      status: mockStatus(),
      statusError: null,
      streamSession: 0,
    })
    vi.spyOn(api, 'startRecording').mockResolvedValue({ success: true })
    vi.spyOn(api, 'stopRecording').mockResolvedValue({ success: true })
  })

  it('switches feature tabs from the tab bar', async () => {
    render(<App />)
    expect(screen.getByText('Recording page')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: /Analysis/i }))
    expect(await screen.findByText('Analysis page')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: /Settings/i }))
    expect(await screen.findByText('Settings page')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: /Camera 1/i }))
    expect(await screen.findByText('Setup cam 1')).toBeInTheDocument()
  })

  it('Space toggles recording when on recording tab', async () => {
    render(<App />)
    await userEvent.keyboard(' ')
    await waitFor(() => expect(api.startRecording).toHaveBeenCalled())
  })
})
