import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Toolbar } from '@/components/toolbar/Toolbar'

describe('Toolbar', () => {
  const defaultProps = {
    zoom: 1,
    showGrid: true,
    showNetLabels: true,
    showValues: true,
    onZoomIn: vi.fn(),
    onZoomOut: vi.fn(),
    onZoomReset: vi.fn(),
    onToggleGrid: vi.fn(),
    onToggleNetLabels: vi.fn(),
    onToggleValues: vi.fn(),
    onOpenSettings: vi.fn(),
  }

  it('should render zoom percentage', () => {
    render(<Toolbar {...defaultProps} zoom={1.5} />)
    expect(screen.getByText('150%')).toBeInTheDocument()
  })

  it('should call onZoomIn when zoom in button is clicked', () => {
    const onZoomIn = vi.fn()
    render(<Toolbar {...defaultProps} onZoomIn={onZoomIn} />)

    const zoomInButton = screen.getByTitle('Zoom in')
    fireEvent.click(zoomInButton)

    expect(onZoomIn).toHaveBeenCalled()
  })

  it('should call onZoomOut when zoom out button is clicked', () => {
    const onZoomOut = vi.fn()
    render(<Toolbar {...defaultProps} onZoomOut={onZoomOut} />)

    const zoomOutButton = screen.getByTitle('Zoom out')
    fireEvent.click(zoomOutButton)

    expect(onZoomOut).toHaveBeenCalled()
  })

  it('should call onZoomReset when reset button is clicked', () => {
    const onZoomReset = vi.fn()
    render(<Toolbar {...defaultProps} onZoomReset={onZoomReset} />)

    const resetButton = screen.getByTitle('Reset zoom')
    fireEvent.click(resetButton)

    expect(onZoomReset).toHaveBeenCalled()
  })

  it('should call onToggleGrid when grid button is clicked', () => {
    const onToggleGrid = vi.fn()
    render(<Toolbar {...defaultProps} onToggleGrid={onToggleGrid} />)

    const gridButton = screen.getByTitle('Hide grid')
    fireEvent.click(gridButton)

    expect(onToggleGrid).toHaveBeenCalled()
  })

  it('should show "Show grid" tooltip when grid is hidden', () => {
    render(<Toolbar {...defaultProps} showGrid={false} />)
    expect(screen.getByTitle('Show grid')).toBeInTheDocument()
  })

  it('should call onOpenSettings when settings button is clicked', () => {
    const onOpenSettings = vi.fn()
    render(<Toolbar {...defaultProps} onOpenSettings={onOpenSettings} />)

    const settingsButton = screen.getByTitle('Settings')
    fireEvent.click(settingsButton)

    expect(onOpenSettings).toHaveBeenCalled()
  })
})
