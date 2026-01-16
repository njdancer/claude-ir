import { test, expect } from '@playwright/test'

const CIRCUIT_FOR_FILTERING = `# Filter Test Circuit

[VCC]: net
[GND]: net
[SIGNAL]: net

[R1]: resistor(10k)
[R2]: resistor(20k)
[R3]: resistor(30k)
[C1]: capacitor(100nF)
[C2]: capacitor(200nF)

[VCC --- R1.1]
[R1.2 --- SIGNAL]
[SIGNAL --- R2.1]
[R2.2 --- C1.1]
[C1.2 --- GND]
[SIGNAL --- R3.1]
[R3.2 --- C2.1]
[C2.2 --- GND]
`

test.describe('Filtering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')

    // Load circuit
    const fileContent = Buffer.from(CIRCUIT_FOR_FILTERING)
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'filter-test.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })
  })

  test('should show filter panel in sidebar', async ({ page }) => {
    // Filter tab should be visible
    await expect(page.getByRole('tab', { name: /filter/i })).toBeVisible()
  })

  test('should have filter mode dropdown', async ({ page }) => {
    // Should have filter mode selector showing "Show All" by default
    await expect(page.getByText('Filter Mode')).toBeVisible()
    await expect(page.getByText('Show All')).toBeVisible()
  })

  test('should filter by net when selecting net mode', async ({ page }) => {
    // Click the filter mode dropdown
    const filterModeSelect = page.getByRole('combobox').first()
    await filterModeSelect.click()

    // Select "Filter by Net" option
    await page.getByRole('option', { name: /Filter by Net/i }).click()

    // Should show net selection UI with "Selected Nets" label
    await expect(page.getByText('Selected Nets')).toBeVisible()
  })

  test('should filter by component when selecting component mode', async ({ page }) => {
    // Click the filter mode dropdown
    const filterModeSelect = page.getByRole('combobox').first()
    await filterModeSelect.click()

    // Select "Filter by Component" option
    await page.getByRole('option', { name: /Filter by Component/i }).click()

    // Should show component selection UI
    await expect(page.getByText('Selected Components')).toBeVisible()
  })

  test('should show clear button when filter is active', async ({ page }) => {
    // Select net filter mode
    const filterModeSelect = page.getByRole('combobox').first()
    await filterModeSelect.click()
    await page.getByRole('option', { name: /Filter by Net/i }).click()

    // Clear button should appear (since we're not in "all" mode)
    await expect(page.getByRole('button', { name: /clear/i })).toBeVisible()
  })

  test('should reset to show all when clicking clear', async ({ page }) => {
    // Select net filter mode
    const filterModeSelect = page.getByRole('combobox').first()
    await filterModeSelect.click()
    await page.getByRole('option', { name: /Filter by Net/i }).click()

    // Click clear
    await page.getByRole('button', { name: /clear/i }).click()

    // Should be back to "Show All" mode
    await expect(page.getByText('Show All')).toBeVisible()
  })

  test('should filter by neighborhood when selecting neighborhood mode', async ({ page }) => {
    // Click the filter mode dropdown
    const filterModeSelect = page.getByRole('combobox').first()
    await filterModeSelect.click()

    // Select "Neighborhood View" option
    await page.getByRole('option', { name: /Neighborhood/i }).click()

    // Should show neighborhood UI with center component selector
    await expect(page.getByText('Center Component')).toBeVisible()
    await expect(page.getByText('Depth')).toBeVisible()
  })

  test('should allow selecting center component for neighborhood', async ({ page }) => {
    // Select neighborhood mode
    const filterModeSelect = page.getByRole('combobox').first()
    await filterModeSelect.click()
    await page.getByRole('option', { name: /Neighborhood/i }).click()

    // Click the center component selector
    const centerSelect = page.getByRole('combobox').nth(1)
    await centerSelect.click()

    // Should show component options
    await expect(page.getByRole('option', { name: 'R1' })).toBeVisible()
  })
})
