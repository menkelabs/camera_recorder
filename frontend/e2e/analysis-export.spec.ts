import { expect, test } from '@playwright/test'

test.describe('Analysis export / clip UI (Vue)', () => {
  test('shows export actions when results are available', async ({ page }) => {
    await page.route('**/api/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          cameras_available: false,
          is_recording: false,
          is_analyzing: false,
          fps: 120,
        }),
      })
    })
    await page.route('**/api/analysis/results', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          max_frames: 10,
          frame_index: 0,
          is_analyzing: false,
          has_frames: true,
          camera1: {
            detection_rate: 90,
            current: { phase: 'Address', sway: 0 },
            summary: {},
            timeseries: {},
          },
          camera2: {
            detection_rate: 88,
            current: { shoulder_turn: 10 },
            summary: {},
            timeseries: {},
          },
        }),
      })
    })
    await page.route('**/api/analysis/score**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ score: 80, grade: 'B', strengths: [], focus: [] }),
      })
    })
    await page.route('**/api/analysis/frame**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            max_frames: 10,
            frame_index: 0,
            is_analyzing: false,
            has_frames: true,
            camera1: null,
            camera2: null,
          }),
        })
        return
      }
      await route.fulfill({ status: 204, body: '' })
    })

    await page.goto('/')
    await page.getByRole('tab', { name: '5 Analysis' }).click()
    await expect(page.getByRole('button', { name: 'Export HTML' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Export CSV' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Clip Cam1' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Clip Cam2' })).toBeVisible()
  })
})
