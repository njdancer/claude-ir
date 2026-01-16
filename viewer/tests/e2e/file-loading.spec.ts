import { test, expect } from '@playwright/test'
import path from 'path'

// Sample circuit.md content for testing
const SIMPLE_CIRCUIT = `# Simple Test Circuit

[VCC]: net
[GND]: net

[R1]: resistor(10k)
[C1]: capacitor(100nF)

[VCC --- R1.1]
[R1.2 --- C1.1]
[C1.2 --- GND]
`

const CIRCUIT_WITH_ERRORS = `# Circuit with Issues

[VCC]: net
[VCC]: net  # Duplicate net

[R1]: resistor(10k)
[R1]: resistor(20k)  # Duplicate component
`

test.describe('File Loading', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should show dropzone on welcome screen', async ({ page }) => {
    const dropzone = page.getByText('or click to browse')
    await expect(dropzone).toBeVisible()
  })

  test('should load circuit file via file input', async ({ page }) => {
    // Create a test file
    const fileContent = Buffer.from(SIMPLE_CIRCUIT)

    // Find the file input (hidden) and upload
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'test.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    // Should show the schematic canvas (SVG element)
    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })

    // Should show sidebar with filename
    await expect(page.getByText('test.circuit.md')).toBeVisible()
  })

  test('should display validation warnings for duplicate declarations', async ({ page }) => {
    const fileContent = Buffer.from(CIRCUIT_WITH_ERRORS)

    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'errors.circuit.md',
      mimeType: 'text/markdown',
      buffer: fileContent,
    })

    // Wait for file to load
    await expect(page.locator('svg.w-full')).toBeVisible({ timeout: 5000 })

    // Click on validation tab
    await page.getByRole('tab', { name: /validation/i }).click()

    // Should show validation issues
    await expect(page.getByText(/duplicate/i)).toBeVisible()
  })

  test('should reject non-markdown files', async ({ page }) => {
    const fileContent = Buffer.from('not a circuit file')

    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: fileContent,
    })

    // Should show error
    await expect(page.getByText(/select a .md file/i)).toBeVisible()
  })
})
