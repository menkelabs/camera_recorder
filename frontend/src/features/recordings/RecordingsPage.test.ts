import { render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import RecordingsPage from './RecordingsPage.vue'

const sample = {
  timestamp: '20260715_120000',
  date: '2026-07-15 12:00:00',
  total_size: 2048,
  duration: 2.5,
  favorite: false,
  notes: '',
  tags: ['tempo'],
  unclaimed: true,
  owner_name: null,
}

function mountPage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAppStore().$patch({ tab: 'recordings' })
  return render(RecordingsPage, { global: { plugins: [pinia] } })
}

describe('RecordingsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'listRecordings').mockResolvedValue({
      recordings: [sample],
      count: 1,
      total_size: 2048,
      favorite_count: 0,
      reference_timestamp: null,
    })
  })

  it('renders owner, filters, and claim for unclaimed rows', async () => {
    mountPage()
    expect(await screen.findByText('Unclaimed')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Claim' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '★ Favorites' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Mine' })).toBeTruthy()
  })

  it('requires confirmation before deleting', async () => {
    const del = vi.spyOn(api, 'deleteRecording').mockResolvedValue({ deleted: true })
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    mountPage()
    await screen.findByRole('button', { name: 'Delete' })
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(del).not.toHaveBeenCalled()
  })

  it('saves notes and tags', async () => {
    const update = vi.spyOn(api, 'updateRecordingMeta').mockResolvedValue({
      favorite: false,
      notes: 'nice tempo',
      tags: ['tempo', 'range'],
    })
    mountPage()
    await userEvent.click(await screen.findByRole('button', { name: 'tempo' }))
    const note = screen.getByPlaceholderText('Notes')
    await userEvent.clear(note)
    await userEvent.type(note, 'nice tempo')
    const tags = screen.getByPlaceholderText('Tags, comma-separated')
    await userEvent.clear(tags)
    await userEvent.type(tags, 'tempo, range')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(update).toHaveBeenCalledWith('20260715_120000', {
        notes: 'nice tempo',
        tags: ['tempo', 'range'],
      }),
    )
  })

  it('prefills Compare from the row action', async () => {
    mountPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Compare' }))
    expect(useAppStore().tab).toBe('compare')
    expect(useAppStore().comparePrefill).toEqual({ a: '20260715_120000' })
  })
})
