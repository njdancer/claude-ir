import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { createSymbolRegistry, getSymbolForType } from '@/symbols'
import { SymbolRenderer } from '@/components/canvas/SymbolRenderer'
import type { SymbolRenderContext } from '@/symbols'

describe('Symbol Snapshots', () => {
  const registry = createSymbolRegistry()

  const defaultContext: SymbolRenderContext = {
    x: 0,
    y: 0,
    orientation: 0,
    scale: 1,
    reference: 'TEST',
    selected: false,
    hovered: false,
    highlighted: false,
  }

  // Test all basic component types
  const componentTypes = [
    'resistor',
    'capacitor',
    'inductor',
    'diode',
    'led',
    'transistor',
    'npn',
    'pnp',
    'mosfet',
    'nmos',
    'pmos',
    'opamp',
    'voltage_source',
    'current_source',
    'ground',
    'vcc',
    'vdd',
    'switch',
  ]

  componentTypes.forEach((type) => {
    it(`should render ${type} symbol consistently`, () => {
      const symbol = getSymbolForType(registry, type)

      if (symbol) {
        const { container } = render(
          <svg>
            <SymbolRenderer
              symbol={symbol.definition}
              context={{ ...defaultContext, reference: type.toUpperCase() }}
            />
          </svg>
        )

        // Snapshot the rendered SVG content
        expect(container.innerHTML).toMatchSnapshot()
      }
    })
  })

  it('should render resistor with value', () => {
    const symbol = getSymbolForType(registry, 'resistor')
    if (symbol) {
      const { container } = render(
        <svg>
          <SymbolRenderer
            symbol={symbol.definition}
            context={{ ...defaultContext, reference: 'R1', value: '10k' }}
          />
        </svg>
      )
      expect(container.innerHTML).toMatchSnapshot()
    }
  })

  it('should render selected state', () => {
    const symbol = getSymbolForType(registry, 'resistor')
    if (symbol) {
      const { container } = render(
        <svg>
          <SymbolRenderer
            symbol={symbol.definition}
            context={{ ...defaultContext, selected: true }}
          />
        </svg>
      )
      expect(container.innerHTML).toMatchSnapshot()
    }
  })

  it('should render hovered state', () => {
    const symbol = getSymbolForType(registry, 'resistor')
    if (symbol) {
      const { container } = render(
        <svg>
          <SymbolRenderer
            symbol={symbol.definition}
            context={{ ...defaultContext, hovered: true }}
          />
        </svg>
      )
      expect(container.innerHTML).toMatchSnapshot()
    }
  })

  it('should render rotated symbols', () => {
    const symbol = getSymbolForType(registry, 'resistor')
    if (symbol) {
      const orientations = [0, 90, 180, 270]
      orientations.forEach((orientation) => {
        const { container } = render(
          <svg>
            <SymbolRenderer
              symbol={symbol.definition}
              context={{ ...defaultContext, orientation }}
            />
          </svg>
        )
        expect(container.innerHTML).toMatchSnapshot()
      })
    }
  })
})
