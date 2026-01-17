# Adding New Symbols

This guide explains how to add new schematic symbols to the Circuit Viewer.

## Symbol System Overview

Symbols are defined as SVG path data with metadata about pins, bounding boxes, and rendering options. The symbol registry maps component types to their visual representations.

## Quick Start

1. Create a symbol definition in `src/symbols/definitions.ts`
2. Register the symbol in `src/symbols/registry.ts`
3. Add tests in `tests/unit/symbols/`

## Symbol Definition Structure

```typescript
interface SymbolDefinition {
  id: string // Unique identifier
  name: string // Display name
  standard?: SymbolStandard // 'ieee' or 'iec'
  width: number // Bounding box width
  height: number // Bounding box height
  paths: SymbolPath[] // SVG path definitions
  pins: PinPosition[] // Pin locations
  origin: { x: number; y: number } // Center point
}
```

## Creating a Symbol

### Step 1: Design the SVG Path

Symbols are defined using SVG path commands. The coordinate system:

- Origin (0,0) is typically the center of the symbol
- Positive X is right, positive Y is down
- Standard grid unit is 10px

Example resistor (IEEE style):

```typescript
export const resistorIEEE: SymbolDefinition = {
  id: 'resistor-ieee',
  name: 'Resistor (IEEE)',
  standard: 'ieee',
  width: 60,
  height: 20,
  origin: { x: 30, y: 10 },
  paths: [
    {
      d: 'M 0 10 L 10 10 L 15 0 L 25 20 L 35 0 L 45 20 L 50 10 L 60 10',
      stroke: 'currentColor',
      fill: 'none',
      strokeWidth: 2,
    },
  ],
  pins: [
    { id: '1', x: 0, y: 10, label: '1' },
    { id: '2', x: 60, y: 10, label: '2' },
  ],
}
```

### Step 2: Define Pin Positions

Pins define where wires connect to the symbol:

```typescript
interface PinPosition {
  id: string // Pin identifier (matches connection syntax)
  x: number // X position relative to origin
  y: number // Y position relative to origin
  label?: string // Optional display label
  side?: 'left' | 'right' | 'top' | 'bottom' // Hint for wire routing
}
```

For ICs with many pins, you can generate pins programmatically:

```typescript
function generateICPins(pinCount: number, spacing: number = 20): PinPosition[] {
  const pins: PinPosition[] = []
  const leftPins = Math.ceil(pinCount / 2)
  const rightPins = Math.floor(pinCount / 2)

  for (let i = 0; i < leftPins; i++) {
    pins.push({
      id: String(i + 1),
      x: 0,
      y: i * spacing + spacing,
      side: 'left',
    })
  }

  for (let i = 0; i < rightPins; i++) {
    pins.push({
      id: String(leftPins + rightPins - i),
      x: 80, // IC width
      y: i * spacing + spacing,
      side: 'right',
    })
  }

  return pins
}
```

### Step 3: Register the Symbol

In `src/symbols/registry.ts`, add your symbol to the registry:

```typescript
registerSymbol(registry, {
  definition: myNewSymbol,
  matchTypes: ['my-component', 'mycomp', 'mc'], // Type aliases
  category: 'passive', // 'passive', 'semiconductor', 'ic', 'connector', 'power', 'misc'
})
```

## Symbol Categories

| Category        | Description             | Examples                         |
| --------------- | ----------------------- | -------------------------------- |
| `passive`       | Passive components      | Resistors, capacitors, inductors |
| `semiconductor` | Active semiconductors   | Diodes, transistors, MOSFETs     |
| `ic`            | Integrated circuits     | Microcontrollers, op-amps        |
| `connector`     | Connectors and switches | Headers, buttons, jacks          |
| `power`         | Power symbols           | Ground, VCC, supply              |
| `misc`          | Other symbols           | Junctions, test points           |

## IEEE vs IEC Standards

Some components have different symbols in IEEE and IEC standards:

```typescript
// IEEE resistor (zig-zag)
export const resistorIEEE: SymbolDefinition = {
  id: 'resistor-ieee',
  standard: 'ieee',
  paths: [{ d: 'M 0 10 L 10 10 L 15 0 L 25 20...' }],
  // ...
}

// IEC resistor (rectangle)
export const resistorIEC: SymbolDefinition = {
  id: 'resistor-iec',
  standard: 'iec',
  paths: [{ d: 'M 0 10 L 10 10 L 10 0 L 50 0...' }],
  // ...
}
```

Both are registered with the same `matchTypes`. The registry selects the appropriate symbol based on the current standard setting.

## Advanced: Multi-Path Symbols

Complex symbols can have multiple paths with different styles:

```typescript
export const led: SymbolDefinition = {
  id: 'led',
  name: 'LED',
  width: 40,
  height: 30,
  origin: { x: 20, y: 15 },
  paths: [
    // Diode triangle
    {
      d: 'M 10 0 L 10 30 L 30 15 Z',
      stroke: 'currentColor',
      fill: 'none',
      strokeWidth: 2,
    },
    // Cathode bar
    {
      d: 'M 30 0 L 30 30',
      stroke: 'currentColor',
      fill: 'none',
      strokeWidth: 2,
    },
    // Light arrows
    {
      d: 'M 25 -5 L 35 -10 M 30 0 L 40 -5',
      stroke: 'currentColor',
      fill: 'none',
      strokeWidth: 1.5,
      className: 'led-arrows',
    },
  ],
  pins: [
    { id: 'A', x: 10, y: 15, side: 'left' },
    { id: 'K', x: 30, y: 15, side: 'right' },
  ],
}
```

## Testing Symbols

Add snapshot tests to verify symbol rendering:

```typescript
// tests/unit/symbols/my-symbol.test.tsx
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { SymbolRenderer } from '@/components/canvas/SymbolRenderer'
import { myNewSymbol } from '@/symbols'

describe('MyNewSymbol', () => {
  it('should render correctly', () => {
    const { container } = render(
      <svg>
        <SymbolRenderer
          definition={myNewSymbol}
          x={0}
          y={0}
          orientation={0}
        />
      </svg>
    )
    expect(container).toMatchSnapshot()
  })

  it('should have correct pin positions', () => {
    expect(myNewSymbol.pins).toHaveLength(2)
    expect(myNewSymbol.pins[0].id).toBe('1')
    expect(myNewSymbol.pins[1].id).toBe('2')
  })
})
```

## Symbol Rendering Context

Symbols receive render context for dynamic styling:

```typescript
interface SymbolRenderContext {
  selected: boolean // Is the component selected?
  hovered: boolean // Is the component hovered?
  highlighted: boolean // Is the component part of a highlight group?
  dimmed: boolean // Is the component outside current filter?
  showValue: boolean // Should the value label be shown?
  showRef: boolean // Should the reference label be shown?
}
```

## Common Patterns

### Transistor-Style Symbols

```typescript
export const npnTransistor: SymbolDefinition = {
  id: 'npn',
  name: 'NPN Transistor',
  width: 40,
  height: 50,
  origin: { x: 20, y: 25 },
  paths: [
    // Base line
    { d: 'M 0 25 L 15 25', stroke: 'currentColor', fill: 'none', strokeWidth: 2 },
    // Emitter and collector from base
    { d: 'M 15 10 L 15 40', stroke: 'currentColor', fill: 'none', strokeWidth: 2 },
    { d: 'M 15 15 L 35 5', stroke: 'currentColor', fill: 'none', strokeWidth: 2 },
    { d: 'M 15 35 L 35 45', stroke: 'currentColor', fill: 'none', strokeWidth: 2 },
    // Arrow on emitter
    { d: 'M 28 40 L 35 45 L 30 38', stroke: 'currentColor', fill: 'currentColor', strokeWidth: 1 },
  ],
  pins: [
    { id: 'B', x: 0, y: 25, side: 'left', label: 'B' },
    { id: 'C', x: 35, y: 5, side: 'right', label: 'C' },
    { id: 'E', x: 35, y: 45, side: 'right', label: 'E' },
  ],
}
```

### Generic IC with Variable Pins

```typescript
export function createGenericIC(name: string, pinCount: number): SymbolDefinition {
  const height = Math.max(60, Math.ceil(pinCount / 2) * 20 + 20)
  return {
    id: `ic-${name.toLowerCase()}`,
    name,
    width: 80,
    height,
    origin: { x: 40, y: height / 2 },
    paths: [
      {
        d: `M 10 0 L 70 0 L 70 ${height} L 10 ${height} Z`,
        stroke: 'currentColor',
        fill: '#fff',
        strokeWidth: 2,
      },
      { d: 'M 10 10 A 5 5 0 0 0 10 20', stroke: 'currentColor', fill: 'none', strokeWidth: 1 }, // Notch
    ],
    pins: generateICPins(pinCount),
  }
}
```

## Checklist for New Symbols

- [ ] Symbol has unique `id`
- [ ] Paths use `currentColor` for theme compatibility
- [ ] Pin IDs match expected connection syntax
- [ ] Width and height match actual bounding box
- [ ] Origin is centered appropriately
- [ ] Symbol registered with relevant type aliases
- [ ] Snapshot test added
- [ ] Both IEEE and IEC variants (if applicable)
