import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { RecordingsPage } from './RecordingsPage'

describe('RecordingsPage', () => {
  beforeEach(() => {
    vi.spyOn(api, 'listRecordings').mockResolvedValue({
      count: 1,
      total_size: 2048,
      favorite_count: 1,
      reference_timestamp: '20260715_120000',
      recordings: [
        {
          timestamp: '20260715_120000',
          date: '2026-07-15 12:00',
          duration: 2.5,
          total_size: 2048,
          favorite: true,
          notes: 'nice tempo',
          tags: [],
          is_reference: true,
        },
      ],
    } as never)
  })

  it('lists recordings with favorite and reference markers', async () => {
    render(<RecordingsPage />)
    expect(await screen.findByText('2026-07-15 12:00')).toBeInTheDocument()
    expect(screen.getByTitle('Favorite')).toBeInTheDocument()
    expect(screen.getByTitle('Reference')).toBeInTheDocument()
    expect(screen.getByText('nice tempo')).toBeInTheDocument()
  })
})
