import { render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.vue'
import { api } from './api/client'
import { useAppStore } from './store/appStore'
import { mockStatus } from './test/mockStatus'

vi.mock('./composables/useStatusPoll', () => ({
  useStatusPoll: () => undefined,
}))

vi.mock('./features/setup/CameraSetupPage.vue', () => ({
  default: {
    props: ['cameraNum'],
    template: '<div>Setup cam {{ cameraNum }}</div>',
  },
}))
vi.mock('./features/recording/RecordingPage.vue', () => ({
  default: { template: '<div>Recording page</div>' },
}))
vi.mock('./features/recordings/RecordingsPage.vue', () => ({
  default: { template: '<div>Recordings page</div>' },
}))
vi.mock('./features/analysis/AnalysisPage.vue', () => ({
  default: { template: '<div>Analysis page</div>' },
}))
vi.mock('./features/compare/ComparePage.vue', () => ({
  default: { template: '<div>Compare page</div>' },
}))
vi.mock('./features/progress/ProgressPage.vue', () => ({
  default: { template: '<div>Progress page</div>' },
}))
vi.mock('./features/settings/SettingsPage.vue', () => ({
  default: { template: '<div>Settings page</div>' },
}))

function mountApp() {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAppStore().$patch({
    tab: 'recording',
    status: mockStatus(),
    statusError: null,
    streamSession: 0,
  })
  return render(App, { global: { plugins: [pinia] } })
}

describe('App shell', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'startRecording').mockResolvedValue({ success: true })
    vi.spyOn(api, 'stopRecording').mockResolvedValue({ success: true })
  })

  it('switches feature tabs from the tab bar', async () => {
    mountApp()
    expect(screen.getByText('Recording page')).toBeTruthy()

    await userEvent.click(screen.getByRole('tab', { name: '5 Analysis' }))
    expect(await screen.findByText('Analysis page')).toBeTruthy()

    await userEvent.click(screen.getByRole('tab', { name: '8 Settings' }))
    expect(await screen.findByText('Settings page')).toBeTruthy()

    await userEvent.click(screen.getByRole('tab', { name: '1 Camera 1' }))
    expect(await screen.findByText('Setup cam 1')).toBeTruthy()
  })

  it('Space toggles recording when on recording tab', async () => {
    mountApp()
    await userEvent.keyboard(' ')
    await waitFor(() => expect(api.startRecording).toHaveBeenCalled())
  })
})
