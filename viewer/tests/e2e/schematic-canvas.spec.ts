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

    // Get initial zoom level from display (shows as button text like "100%")
    const zoomDisplay = page.locator('button:has-text("%")')
    const initialText = await zoomDisplay.textContent()
    const initialZoom = parseInt(initialText?.replace('%', '') || '100')

    // Click zoom in
    await zoomInButton.click()

    // Zoom should increase
    const newText = await zoomDisplay.textContent()
    const newZoom = parseInt(newText?.replace('%', '') || '100')
    expect(newZoom).toBeGreaterThan(initialZoom)
  })

  test('should zoom out with toolbar button', async ({ page }) => {
    const zoomOutButton = page.getByRole('button', { name: /zoom out/i })

    // Get initial zoom level
    const zoomDisplay = page.locator('button:has-text("%")')
    const initialText = await zoomDisplay.textContent()
    const initialZoom = parseInt(initialText?.replace('%', '') || '100')

    // Click zoom out
    await zoomOutButton.click()

    // Zoom should decrease
    const newText = await zoomDisplay.textContent()
    const newZoom = parseInt(newText?.replace('%', '') || '100')
    expect(newZoom).toBeLessThan(initialZoom)
  })

  test('should toggle grid visibility', async ({ page }) => {
    // Find grid toggle button (either "Show grid" or "Hide grid")
    const gridToggle = page.getByRole('button', { name: /grid/i })
    const svg = page.locator('svg.w-full')

    // Grid pattern definition should exist initially
    await expect(svg.locator('pattern#grid')).toBeAttached()

    // Grid rect (using the pattern) should exist initially
    await expect(svg.locator('rect[fill="url(#grid)"]')).toBeAttached()

    // Toggle grid off - button click should work
    await gridToggle.click()

    // After toggle, the rect using the pattern should be removed
    await expect(svg.locator('rect[fill="url(#grid)"]')).not.toBeAttached()
  })

  test('should toggle net labels', async ({ page }) => {
    // Find labels toggle button (either "Show labels" or "Hide labels")
    const labelsToggle = page.getByRole('button', { name: /labels/i })

    // Toggle should work without error
    await labelsToggle.click()
    await labelsToggle.click() // Toggle back
  })
})
