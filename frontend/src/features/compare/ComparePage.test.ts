import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../api/client'
import { useAppStore } from '../../store/appStore'
import ComparePage from './ComparePage.vue'

vi.mock('../../components/LineChart.vue', () => ({
  default: { template: '<div data-testid="chart">chart</div>' },
}))

function mountPage() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return render(ComparePage, { global: { plugins: [pinia] } })
}

describe('ComparePage', () => {
  beforeEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.spyOn(api, 'practiceSettings').mockResolvedValue({
      camera_roles: { camera1: 'face_on', camera2: 'dtl' },
      camera_labels: { camera1: 'Face-On', camera2: 'Down-the-Line' },
    })
  })

  it('does not compare the same swing when only one analysis exists', async () => {
    const compare = vi.spyOn(api, 'compare')
    vi.spyOn(api, 'listAnalyses').mockResolvedValue({
      analyses: [{ timestamp: '20260715_120000', date: '2026-07-15 12:00' }],
      count: 1,
    })

    mountPage()
    expect(await screen.findByText(/Only one analyzed swing/)).toBeTruthy()
    expect(compare).not.toHaveBeenCalled()
  })

  it('prefills A from the store and B from the other swing', async () => {
    vi.spyOn(api, 'listAnalyses').mockResolvedValue({
      analyses: [
        { timestamp: '20260715_120000', date: '2026-07-15 12:00', is_reference: true },
        { timestamp: '20260716_120000', date: '2026-07-16 12:00' },
      ],
      count: 2,
      reference_timestamp: '20260715_120000',
    })
    vi.spyOn(api, 'compare').mockResolvedValue({
      swing_a: {},
      swing_b: {},
      deltas: {
        camera1: { max_sway_right: { a: 4, b: 2, delta: -2 } },
        camera2: { max_shoulder_turn: { a: 70, b: 80, delta: 10 } },
      },
    })

    const pinia = createPinia()
    setActivePinia(pinia)
    useAppStore().setComparePrefill({ a: '20260716_120000' })
    render(ComparePage, { global: { plugins: [pinia] } })

    await waitFor(() => expect(api.compare).toHaveBeenCalledWith('20260716_120000', '20260715_120000'))
    expect(await screen.findByText('Face-On')).toBeTruthy()
    expect(screen.getByText('Down-the-Line')).toBeTruthy()
  })
})
