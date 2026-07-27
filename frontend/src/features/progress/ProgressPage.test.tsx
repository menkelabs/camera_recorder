import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { ProgressPage } from './ProgressPage'

vi.mock('../../components/LineChart', () => ({
  LineChart: () => <div data-testid="chart">chart</div>,
}))

describe('ProgressPage', () => {
  beforeEach(() => {
    vi.spyOn(api, 'progress').mockResolvedValue({
      count: 2,
      latest_score: 88,
      latest_grade: 'B',
      points: [
        { timestamp: '20260715_120000', date: 'Jul 15', score: 80 },
        { timestamp: '20260716_120000', date: 'Jul 16', score: 88 },
      ],
      metrics: [{ key: 'score', label: 'Score' }],
      series: { score: [80, 88] },
    } as never)
  })

  it('shows trend summary', async () => {
    render(<ProgressPage />)
    expect(await screen.findByRole('heading', { name: 'Progress' })).toBeInTheDocument()
    expect(screen.getByText(/Swings:/)).toBeInTheDocument()
    expect(screen.getByText(/Latest:/)).toBeInTheDocument()
    expect(screen.getByText(/B\s*88/)).toBeInTheDocument()
  })
})
