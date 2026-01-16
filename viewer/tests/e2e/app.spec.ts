import { test, expect } from '@playwright/test'

test.describe('Circuit Schematic Viewer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display welcome screen on initial load', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Circuit Schematic Viewer' })).toBeVisible()
    await expect(page.getByText(/visualize and explore/)).toBeVisible()
  })

  test('should have a working toolbar', async ({ page }) => {
    // Toolbar should be visible
    await expect(page.getByRole('button', { name: /zoom in/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /zoom out/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /settings/i })).toBeVisible()
  })

  test('should open settings dialog', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText('Symbol Standard')).toBeVisible()
  })

  test('should toggle symbol standard in settings', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click()

    // Find and click the symbol standard selector
    const symbolSelect = page.getByRole('combobox').first()
    await symbolSelect.click()

    // Should have IEEE and IEC options
    await expect(page.getByRole('option', { name: /IEEE/i })).toBeVisible()
    await expect(page.getByRole('option', { name: /IEC/i })).toBeVisible()
  })

  test('should close settings dialog', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()

    // Close dialog by clicking the close button or outside
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 5000 })
  })
})
