import { render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import ProgressPage from './ProgressPage.vue'

vi.mock('../../components/LineChart.vue', () => ({
  default: { template: '<div data-testid="chart">chart</div>' },
}))

describe('ProgressPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows empty state without a chart when there are no swings', async () => {
    vi.spyOn(api, 'progress').mockResolvedValue({
      count: 0,
      metrics: [{ key: 'score', label: 'Score' }],
      points: [],
      series: { score: [] },
    })
    render(ProgressPage)
    expect(await screen.findByText(/No analyzed swings yet/)).toBeTruthy()
    expect(screen.queryByTestId('chart')).toBeNull()
  })

  it('renders summary and chart when swings exist', async () => {
    vi.spyOn(api, 'progress').mockResolvedValue({
      count: 2,
      latest_grade: 'B',
      latest_score: 82,
      score_delta: 8,
      metrics: [
        { key: 'score', label: 'Score' },
        { key: 'max_shoulder_turn', label: 'Shoulder turn' },
      ],
      points: [
        { timestamp: '20260715_120000', date: '2026-07-15', metrics: {} },
        { timestamp: '20260716_120000', date: '2026-07-16', metrics: {} },
      ],
      series: { score: [74, 82], max_shoulder_turn: [70, 80] },
    })
    render(ProgressPage)
    expect(await screen.findByText('B')).toBeTruthy()
    expect(screen.getByTestId('chart')).toBeTruthy()
    expect(screen.getByText('Shoulder turn')).toBeTruthy()
  })
})
