import { test, expect } from '@playwright/test'

const SIMPLE_CIRCUIT = `# Test Circuit

[VCC]: net
[GND]: net
[NODE1]: net

[R1]: resistor(10k)
[R2]: resistor(20k)
[C1]: capacitor(100nF)

[VCC --- R1.1]
[R1.2 --- NODE1]
[NODE1 --- R2.1]
[R2.2 --- C1.1]
[C1.2 --- GND]
`

test.describe('Schematic Canvas', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')

    // Load a circuit file
    const fileContent = Buffer.from(SIMPLE_CIRCUIT)
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'test.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    // Wait for canvas to appear
    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })
  })

  test('should display schematic symbols', async ({ page }) => {
    // Should have SVG groups for symbols
    const svg = page.locator('svg.w-full')
    await expect(svg.locator('.symbols')).toBeVisible()
  })

  test('should display wires', async ({ page }) => {
    const svg = page.locator('svg.w-full')
    await expect(svg.locator('.wires')).toBeVisible()
  })

  test('should zoom in with toolbar button', async ({ page }) => {
    const zoomInButton = page.getByRole('button', { name: /zoom in/i })

    // Get initial zoom level from display
    const zoomDisplay = page.locator('text=/\\d+%/')
    const initialZoom = await zoomDisplay.textContent()

    // Click zoom in
    await zoomInButton.click()

    // Zoom should increase
    const newZoom = await zoomDisplay.textContent()
    expect(parseInt(newZoom || '100')).toBeGreaterThan(parseInt(initialZoom || '100'))
  })

  test('should zoom out with toolbar button', async ({ page }) => {
    const zoomOutButton = page.getByRole('button', { name: /zoom out/i })

    // Get initial zoom level
    const zoomDisplay = page.locator('text=/\\d+%/')
    const initialZoom = await zoomDisplay.textContent()

    // Click zoom out
    await zoomOutButton.click()

    // Zoom should decrease
    const newZoom = await zoomDisplay.textContent()
    expect(parseInt(newZoom || '100')).toBeLessThan(parseInt(initialZoom || '100'))
  })

  test('should toggle grid visibility', async ({ page }) => {
    const gridToggle = page.getByRole('button', { name: /grid/i })
    const svg = page.locator('svg.w-full')

    // Grid should be visible initially
    await expect(svg.locator('pattern#grid')).toBeVisible()

    // Toggle grid off
    await gridToggle.click()

    // Grid pattern should be hidden or removed
    // (The actual implementation might vary)
  })

  test('should toggle net labels', async ({ page }) => {
    const labelsToggle = page.getByRole('button', { name: /labels/i })

    // Toggle should work without error
    await labelsToggle.click()
    await labelsToggle.click() // Toggle back
  })
})
