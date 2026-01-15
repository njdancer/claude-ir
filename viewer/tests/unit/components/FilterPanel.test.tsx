import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FilterPanel } from '@/components/sidebar/FilterPanel'
import type { FilterConfig } from '@/state'

describe('FilterPanel', () => {
  const defaultFilter: FilterConfig = {
    mode: 'all',
    nets: [],
    components: [],
    neighborhoodCenter: null,
    neighborhoodDepth: 1,
  }

  const netNames = ['VCC', 'GND', 'SDA', 'SCL']
  const componentRefs = ['U1', 'R1', 'C1', 'D1']

  it('should render filter mode selector', () => {
    const onFilterChange = vi.fn()
    const onResetFilter = vi.fn()

    render(
      <FilterPanel
        filter={defaultFilter}
        netNames={netNames}
        componentRefs={componentRefs}
        onFilterChange={onFilterChange}
        onResetFilter={onResetFilter}
      />
    )

    expect(screen.getByText('Filters')).toBeInTheDocument()
    expect(screen.getByText('Filter Mode')).toBeInTheDocument()
  })

  it('should show clear button when filtered', () => {
    const onFilterChange = vi.fn()
    const onResetFilter = vi.fn()

    const filteredConfig: FilterConfig = {
      ...defaultFilter,
      mode: 'net',
      nets: ['VCC'],
    }

    render(
      <FilterPanel
        filter={filteredConfig}
        netNames={netNames}
        componentRefs={componentRefs}
        onFilterChange={onFilterChange}
        onResetFilter={onResetFilter}
      />
    )

    expect(screen.getByText('Clear')).toBeInTheDocument()
  })

  it('should not show clear button when not filtered', () => {
    const onFilterChange = vi.fn()
    const onResetFilter = vi.fn()

    render(
      <FilterPanel
        filter={defaultFilter}
        netNames={netNames}
        componentRefs={componentRefs}
        onFilterChange={onFilterChange}
        onResetFilter={onResetFilter}
      />
    )

    expect(screen.queryByText('Clear')).not.toBeInTheDocument()
  })

  it('should show net list in net filter mode', () => {
    const onFilterChange = vi.fn()
    const onResetFilter = vi.fn()

    const netFilter: FilterConfig = {
      ...defaultFilter,
      mode: 'net',
    }

    render(
      <FilterPanel
        filter={netFilter}
        netNames={netNames}
        componentRefs={componentRefs}
        onFilterChange={onFilterChange}
        onResetFilter={onResetFilter}
      />
    )

    // Search input should be visible
    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
    // Net names should be visible
    expect(screen.getByText('VCC')).toBeInTheDocument()
    expect(screen.getByText('GND')).toBeInTheDocument()
  })

  it('should show component list in component filter mode', () => {
    const onFilterChange = vi.fn()
    const onResetFilter = vi.fn()

    const componentFilter: FilterConfig = {
      ...defaultFilter,
      mode: 'component',
    }

    render(
      <FilterPanel
        filter={componentFilter}
        netNames={netNames}
        componentRefs={componentRefs}
        onFilterChange={onFilterChange}
        onResetFilter={onResetFilter}
      />
    )

    // Component refs should be visible
    expect(screen.getByText('U1')).toBeInTheDocument()
    expect(screen.getByText('R1')).toBeInTheDocument()
  })

  it('should filter nets by search term', () => {
    const onFilterChange = vi.fn()
    const onResetFilter = vi.fn()

    const netFilter: FilterConfig = {
      ...defaultFilter,
      mode: 'net',
    }

    render(
      <FilterPanel
        filter={netFilter}
        netNames={netNames}
        componentRefs={componentRefs}
        onFilterChange={onFilterChange}
        onResetFilter={onResetFilter}
      />
    )

    const searchInput = screen.getByPlaceholderText('Search...')
    fireEvent.change(searchInput, { target: { value: 'V' } })

    // Only VCC should be visible after filtering
    expect(screen.getByText('VCC')).toBeInTheDocument()
    expect(screen.queryByText('GND')).not.toBeInTheDocument()
  })

  it('should call onResetFilter when clear button is clicked', () => {
    const onFilterChange = vi.fn()
    const onResetFilter = vi.fn()

    const filteredConfig: FilterConfig = {
      ...defaultFilter,
      mode: 'net',
      nets: ['VCC'],
    }

    render(
      <FilterPanel
        filter={filteredConfig}
        netNames={netNames}
        componentRefs={componentRefs}
        onFilterChange={onFilterChange}
        onResetFilter={onResetFilter}
      />
    )

    fireEvent.click(screen.getByText('Clear'))
    expect(onResetFilter).toHaveBeenCalled()
  })
})
