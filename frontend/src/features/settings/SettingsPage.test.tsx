import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { SettingsPage } from './SettingsPage'

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.spyOn(api, 'practiceSettings').mockResolvedValue({
      camera_roles: { camera1: 'face_on', camera2: 'dtl' },
      metronome: { enabled: false, bpm: 60 },
    } as never)
    vi.spyOn(api, 'archiveConfig').mockResolvedValue({
      archive_path: '/tmp/archive',
      configured: true,
      available: true,
    } as never)
    vi.spyOn(api, 'archiveStatus').mockResolvedValue({
      archived_timestamps: [],
      archived_count: 0,
      archive_path: '/tmp/archive',
      available: true,
      disk: { total: 1000, used: 200, free: 800, percent: 20 },
    } as never)
    vi.spyOn(api, 'listRecordings').mockResolvedValue({
      count: 3,
      total_size: 0,
      recordings: [],
    } as never)
  })

  it('loads roles and saves archive path', async () => {
    const setCfg = vi.spyOn(api, 'setArchiveConfig').mockResolvedValue({
      success: true,
      archive_path: '/tmp/new',
    })
    render(<SettingsPage />)
    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    expect(screen.getByDisplayValue('/tmp/archive')).toBeInTheDocument()

    const input = screen.getByDisplayValue('/tmp/archive')
    await userEvent.clear(input)
    await userEvent.type(input, '/tmp/new')
    await userEvent.click(screen.getByRole('button', { name: /Save path|Save/i }))
    await waitFor(() => expect(setCfg).toHaveBeenCalled())
  })
})
