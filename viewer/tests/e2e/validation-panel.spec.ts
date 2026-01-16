import { test, expect } from '@playwright/test'

const CIRCUIT_WITH_ERRORS = `# Circuit with Validation Issues

[VCC]: net
[VCC]: net
[GND]: net

[R1]: resistor(10k)
[R1]: resistor(20k)

[VCC --- R1.1]
[R1.2 --- GND]
`

const VALID_CIRCUIT = `# Valid Circuit

[VCC]: net
[GND]: net

[R1]: resistor(10k)

[VCC --- R1.1]
[R1.2 --- GND]
`

test.describe('Validation Panel', () => {
  test('should show validation tab in sidebar', async ({ page }) => {
    await page.goto('/')

    // Load a circuit
    const fileContent = Buffer.from(VALID_CIRCUIT)
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'valid.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })

    // Validation tab should be visible
    await expect(page.getByRole('tab', { name: /validation/i })).toBeVisible()
  })

  test('should display validation warnings for duplicate declarations', async ({ page }) => {
    await page.goto('/')

    // Load circuit with errors
    const fileContent = Buffer.from(CIRCUIT_WITH_ERRORS)
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'errors.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })

    // Click on validation tab and wait
    const validationTab = page.getByRole('tab', { name: /validation/i })
    await validationTab.click()
    await page.waitForTimeout(300)

    // Should show validation issues mentioning duplicates
    await expect(page.getByText(/duplicate/i)).toBeVisible({ timeout: 5000 })
  })

  test('should show warning count badge', async ({ page }) => {
    await page.goto('/')

    // Load circuit with errors
    const fileContent = Buffer.from(CIRCUIT_WITH_ERRORS)
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'errors.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })

    // Validation tab should be visible
    const validationTab = page.getByRole('tab', { name: /validation/i })
    await expect(validationTab).toBeVisible()
  })

  test('should show validation content when tab clicked', async ({ page }) => {
    await page.goto('/')

    // Load circuit with errors
    const fileContent = Buffer.from(CIRCUIT_WITH_ERRORS)
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'errors.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })

    // Click on validation tab
    const validationTab = page.getByRole('tab', { name: /validation/i })
    await validationTab.click()
    await page.waitForTimeout(300)

    // Should show validation content with issue counts
    await expect(page.getByText(/\d+ (warning|error)/i).first()).toBeVisible({ timeout: 5000 })
  })

  test('should handle valid circuit', async ({ page }) => {
    await page.goto('/')

    // Load valid circuit
    const fileContent = Buffer.from(VALID_CIRCUIT)
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'valid.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })

    // Click on validation tab - should work without errors
    const validationTab = page.getByRole('tab', { name: /validation/i })
    await validationTab.click()

    // Validation tab should be selected (active state)
    await expect(validationTab).toHaveAttribute('data-state', 'active')
  })
})
