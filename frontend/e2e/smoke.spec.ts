import { expect, test } from '@playwright/test'

test.describe('GUI Vue smoke (Flask + Vue dist)', () => {
  test('serves Vue shell with all tabs', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('#app')).toBeVisible()
    await expect(page.getByRole('tab', { name: '3 Recording' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '5 Analysis' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '8 Settings' })).toBeVisible()
  })

  test('tab navigation mounts feature pages', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('tab', { name: '5 Analysis' }).click()
    await expect(page.getByRole('heading', { name: 'Analysis' })).toBeVisible()

    await page.getByRole('tab', { name: '4 Recordings' }).click()
    await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible()

    await page.getByRole('tab', { name: '6 Compare' }).click()
    await expect(page.getByRole('heading', { name: /Compare Swings/i })).toBeVisible()

    await page.getByRole('tab', { name: '7 Progress' }).click()
    await expect(page.getByRole('heading', { name: 'Progress' })).toBeVisible()

    await page.getByRole('tab', { name: '8 Settings' }).click()
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
  })

  test('status API responds for the UI poll', async ({ request }) => {
    const resp = await request.get('/api/status')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('is_recording')
    expect(data).toHaveProperty('cameras_available')
  })

  test('legacy bookmarks redirect to the Vue app', async ({ page }) => {
    await page.goto('/legacy')
    await expect(page).toHaveURL(/\/$/)
    await expect(page.locator('#app')).toBeVisible()
  })
})
