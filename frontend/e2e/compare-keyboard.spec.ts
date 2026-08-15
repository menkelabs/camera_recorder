import { expect, test } from '@playwright/test'

test.describe('Compare + keyboard regressions', () => {
  test('Compare shows a same-swing message when only one analysis exists', async ({ page }) => {
    await page.route('**/api/analyses', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          analyses: [{ timestamp: '20260715_120000', date: '2026-07-15 12:00' }],
          count: 1,
        }),
      })
    })
    await page.route('**/api/practice/settings', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          camera_roles: { camera1: 'face_on', camera2: 'dtl' },
          camera_labels: { camera1: 'Face-On', camera2: 'Down-the-Line' },
        }),
      })
    })
    await page.route('**/api/compare**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'should not be called' }),
      })
    })

    await page.goto('/')
    await page.getByRole('tab', { name: '6 Compare' }).click()
    await expect(page.getByText(/Only one analyzed swing/i)).toBeVisible()
  })

  test('Analysis history picker lists saved swings', async ({ page }) => {
    await page.route('**/api/analyses', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          analyses: [{ timestamp: '20260715_120000', date: '2026-07-15 12:00' }],
          count: 1,
        }),
      })
    })
    await page.route('**/api/analysis/results**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          max_frames: 0,
          frame_index: 0,
          is_analyzing: false,
          has_frames: false,
          source: 'live',
          camera1: null,
          camera2: null,
        }),
      })
    })

    await page.goto('/')
    await page.getByRole('tab', { name: '5 Analysis' }).click()
    const picker = page.getByLabel('Swing')
    await expect(picker).toBeVisible()
    await expect(picker.getByRole('option', { name: 'Latest session' })).toBeAttached()
    await expect(picker.getByRole('option', { name: /2026-07-15/ })).toBeAttached()
  })

  test('Space on Analysis does not start a recording', async ({ page }) => {
    let started = false
    await page.route('**/api/recording/start', async (route) => {
      started = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    })

    await page.goto('/')
    await page.getByRole('tab', { name: '5 Analysis' }).click()
    await expect(page.getByRole('heading', { name: 'Analysis' })).toBeVisible()
    await page.keyboard.press('Space')
    await page.waitForTimeout(200)
    expect(started).toBeFalsy()
  })
})
