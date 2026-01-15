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
    await expect(page.getByRole('tab', { name: /filter/i })).toBeVisible()
  })

  test('should have filter mode options', async ({ page }) => {
    // Should have all, net, component, neighborhood mode options
    await expect(page.getByText('Show All')).toBeVisible()
  })

  test('should filter by net', async ({ page }) => {
    // Select net filter mode
    const netModeButton = page.getByRole('button', { name: /by net/i })
    await netModeButton.click()

    // Should show net dropdown
    await expect(page.getByText(/select.*net/i)).toBeVisible()
  })

  test('should filter by component', async ({ page }) => {
    // Select component filter mode
    const componentModeButton = page.getByRole('button', { name: /by component/i })
    await componentModeButton.click()

    // Should show component dropdown
    await expect(page.getByText(/select.*component/i)).toBeVisible()
  })

  test('should have clear filter button', async ({ page }) => {
    // Select a filter mode first
    const netModeButton = page.getByRole('button', { name: /by net/i })
    await netModeButton.click()

    // Clear button should appear
    await expect(page.getByRole('button', { name: /clear/i })).toBeVisible()
  })

  test('should reset to show all', async ({ page }) => {
    // Select net mode
    const netModeButton = page.getByRole('button', { name: /by net/i })
    await netModeButton.click()

    // Click show all to reset
    const showAllButton = page.getByRole('button', { name: /show all/i })
    await showAllButton.click()

    // Should be back to all mode
    await expect(showAllButton).toHaveAttribute('data-state', 'on')
  })
})
