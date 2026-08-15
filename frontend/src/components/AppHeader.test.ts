import { cleanup, render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import { useAppStore } from '../store/appStore'
import { mockStatus } from '../test/mockStatus'
import AppHeader from './AppHeader.vue'

function mountHeader(overrides = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAppStore().$patch({
    status: mockStatus({
      users: [
        { id: 1, name: 'Player 1', has_pin: false, is_active: true },
        { id: 2, name: 'Jordan', has_pin: true, is_active: false },
      ],
      active_user: { id: 1, name: 'Player 1', has_pin: false, is_active: true },
      ...overrides,
    }),
  })
  return render(AppHeader, { global: { plugins: [pinia] } })
}

describe('AppHeader', () => {
  beforeEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('asks for a PIN when switching to a locked player', async () => {
    const switchUser = vi.spyOn(api, 'setActiveUser')
    mountHeader()
    await userEvent.selectOptions(screen.getByLabelText('Player'), '2')
    expect(await screen.findByPlaceholderText('PIN')).toBeTruthy()
    expect(switchUser).not.toHaveBeenCalled()
  })

  it('disables player switching while recording', () => {
    mountHeader({ is_recording: true })
    expect(screen.getByLabelText('Player')).toBeDisabled()
  })
})
