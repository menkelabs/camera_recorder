import { expect, test } from '@playwright/test'

test.describe('GUI v2 smoke (Flask + React dist)', () => {
  test('serves React shell with all tabs', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('#root')).toBeVisible()
    // Accessible names include shortcut digits ("3 Recording" vs "4 Recordings")
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
    await expect(page.getByRole('link', { name: '/legacy' })).toBeVisible()
  })

  test('status API responds for the UI poll', async ({ request }) => {
    const resp = await request.get('/api/status')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('is_recording')
    expect(data).toHaveProperty('cameras_available')
  })

  test('legacy route still serves v1 template', async ({ page }) => {
    await page.goto('/legacy')
    await expect(page.locator('body')).toContainText('Camera Setup')
    await expect(page.locator('body')).toContainText('Pre-Record Checklist')
  })
})
