import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FileDropzone } from '@/components/file/FileDropzone'

// Mock File with text() method
class MockFile extends File {
  private content: string

  constructor(content: string[], name: string, options?: FilePropertyBag) {
    super(content, name, options)
    this.content = content.join('')
  }

  async text(): Promise<string> {
    return this.content
  }
}

describe('FileDropzone', () => {
  it('should render dropzone with instructions', () => {
    const onFileLoad = vi.fn()
    render(<FileDropzone onFileLoad={onFileLoad} />)

    expect(screen.getByText('Drop a .circuit.md file here')).toBeInTheDocument()
    expect(screen.getByText('or click to browse')).toBeInTheDocument()
  })

  it('should show drag over state', () => {
    const onFileLoad = vi.fn()
    render(<FileDropzone onFileLoad={onFileLoad} />)

    const dropzone = screen.getByText('Drop a .circuit.md file here').parentElement?.parentElement
    if (dropzone) {
      fireEvent.dragOver(dropzone)
      expect(screen.getByText('Drop file here')).toBeInTheDocument()
    }
  })

  it('should accept .md files', async () => {
    const onFileLoad = vi.fn()
    render(<FileDropzone onFileLoad={onFileLoad} />)

    const file = new MockFile(['[VCC]: net'], 'test.circuit.md', { type: 'text/markdown' })
    const input = document.querySelector('input[type="file"]')

    if (input) {
      Object.defineProperty(input, 'files', {
        value: [file],
      })
      fireEvent.change(input)

      await waitFor(() => {
        expect(onFileLoad).toHaveBeenCalledWith('test.circuit.md', '[VCC]: net')
      })
    }
  })

  it('should reject non-md files', async () => {
    const onFileLoad = vi.fn()
    const onError = vi.fn()
    render(<FileDropzone onFileLoad={onFileLoad} onError={onError} />)

    const file = new MockFile(['test'], 'test.txt', { type: 'text/plain' })
    const input = document.querySelector('input[type="file"]')

    if (input) {
      Object.defineProperty(input, 'files', {
        value: [file],
      })
      fireEvent.change(input)

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Please select a .md file')
      })
    }
  })
})
