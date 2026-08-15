import { cleanup, render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import { mockStatus } from '../../test/mockStatus'
import SettingsPage from './SettingsPage.vue'

function mountPage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAppStore().$patch({ status: mockStatus() })
  return render(SettingsPage, { global: { plugins: [pinia] } })
}

describe('SettingsPage', () => {
  beforeEach(() => {
    cleanup()
    vi.restoreAllMocks()
    window.confirm = vi.fn().mockReturnValue(false)
    vi.spyOn(api, 'practiceSettings').mockResolvedValue({
      camera_roles: { camera1: 'face_on', camera2: 'dtl' },
      camera_labels: { camera1: 'Face-On', camera2: 'Down-the-Line' },
    })
    vi.spyOn(api, 'archiveConfig').mockResolvedValue({
      archive_path: '',
      configured: false,
      available: false,
    })
    vi.spyOn(api, 'archiveStatus').mockResolvedValue({
      archived_timestamps: [],
      archived_count: 0,
      archive_path: '',
      available: false,
    })
    vi.spyOn(api, 'listRecordings').mockResolvedValue({
      recordings: [],
      count: 0,
      total_size: 0,
    })
    vi.spyOn(api, 'listUsers').mockResolvedValue({
      users: [
        { id: 1, name: 'Player 1', has_pin: false, is_active: true },
        { id: 2, name: 'Jordan', has_pin: true, is_active: false },
      ],
      active_user: { id: 1, name: 'Player 1', has_pin: false, is_active: true },
    })
  })

  it('rejects short PINs before calling the API', async () => {
    const create = vi.spyOn(api, 'createUser')
    mountPage()
    await screen.findByText('Players')
    await userEvent.type(screen.getByPlaceholderText('New player name'), 'Pat')
    await userEvent.type(screen.getByPlaceholderText('Optional PIN'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Add player' }))
    expect(await screen.findByText('PIN must be at least 4 characters')).toBeTruthy()
    expect(create).not.toHaveBeenCalled()
  })

  it('asks for confirmation before deleting a player', async () => {
    const del = vi.spyOn(api, 'deleteUser')
    mountPage()
    const buttons = await screen.findAllByRole('button', { name: 'Delete' })
    await userEvent.click(buttons[1])
    expect(del).not.toHaveBeenCalled()
  })
})
