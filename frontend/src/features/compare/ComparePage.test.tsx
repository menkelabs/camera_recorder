import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { ComparePage } from './ComparePage'

vi.mock('../../components/LineChart', () => ({
  LineChart: () => <div data-testid="chart">chart</div>,
}))

describe('ComparePage', () => {
  beforeEach(() => {
    vi.spyOn(api, 'listAnalyses').mockResolvedValue({
      count: 2,
      analyses: [
        { timestamp: '20260715_120000', date: 'A', score: 80, grade: 'B' },
        { timestamp: '20260716_120000', date: 'B', score: 70, grade: 'C' },
      ],
      reference_timestamp: '20260715_120000',
    } as never)
  })

  it('loads analyses and auto-compares selection', async () => {
    const compare = vi.spyOn(api, 'compare').mockResolvedValue({
      swing_a: { timestamp: '20260715_120000', camera2: { shoulder_turn: [0, 40] } },
      swing_b: { timestamp: '20260716_120000', camera2: { shoulder_turn: [0, 35] } },
      deltas: {
        camera1: null,
        camera2: {
          max_shoulder_turn: { a: 45, b: 40, delta: -5 },
        },
      },
    } as never)

    render(<ComparePage />)
    expect(await screen.findByRole('heading', { name: /Compare Swings/i })).toBeInTheDocument()
    await waitFor(() => expect(compare).toHaveBeenCalled())
    expect(await screen.findByText(/max shoulder turn/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Refresh/i }))
    await waitFor(() => expect(compare.mock.calls.length).toBeGreaterThan(1))
  })
})
