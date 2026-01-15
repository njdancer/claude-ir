import type { SymbolDefinition } from './types'

/**
 * IEEE (American) resistor symbol - zigzag pattern
 */
export const resistorIEEE: SymbolDefinition = {
  id: 'resistor-ieee',
  name: 'Resistor (IEEE)',
  width: 60,
  height: 20,
  paths: [
    {
      d: 'M -30 0 L -20 0 L -15 -8 L -5 8 L 5 -8 L 15 8 L 20 0 L 30 0',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -30, y: 0, label: '1', direction: 'left' },
    { x: 30, y: 0, label: '2', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: true,
}

/**
 * IEC (European) resistor symbol - rectangle
 */
export const resistorIEC: SymbolDefinition = {
  id: 'resistor-iec',
  name: 'Resistor (IEC)',
  width: 60,
  height: 20,
  paths: [
    {
      d: 'M -30 0 L -20 0 M -20 -8 L -20 8 L 20 8 L 20 -8 L -20 -8 M 20 0 L 30 0',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -30, y: 0, label: '1', direction: 'left' },
    { x: 30, y: 0, label: '2', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'iec',
  hasValueLabel: true,
}

/**
 * Capacitor symbol (non-polarized)
 */
export const capacitor: SymbolDefinition = {
  id: 'capacitor',
  name: 'Capacitor',
  width: 40,
  height: 30,
  paths: [
    {
      d: 'M -20 0 L -5 0 M -5 -12 L -5 12 M 5 -12 L 5 12 M 5 0 L 20 0',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: 0, label: '1', direction: 'left' },
    { x: 20, y: 0, label: '2', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: true,
}

/**
 * Polarized capacitor symbol (electrolytic)
 */
export const capacitorPolarized: SymbolDefinition = {
  id: 'capacitor-polarized',
  name: 'Polarized Capacitor',
  width: 40,
  height: 30,
  paths: [
    // Capacitor plates
    {
      d: 'M -20 0 L -5 0 M -5 -12 L -5 12 M 5 0 L 20 0',
      strokeWidth: 2,
    },
    // Curved plate (negative)
    {
      d: 'M 5 -12 Q 8 0 5 12',
      strokeWidth: 2,
    },
    // Plus sign
    {
      d: 'M -12 -8 L -12 -4 M -14 -6 L -10 -6',
      strokeWidth: 1.5,
    },
  ],
  pins: [
    { x: -20, y: 0, label: '+', direction: 'left' },
    { x: 20, y: 0, label: '-', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: true,
}

/**
 * Inductor symbol - humps/coils
 */
export const inductor: SymbolDefinition = {
  id: 'inductor',
  name: 'Inductor',
  width: 60,
  height: 20,
  paths: [
    {
      d: 'M -30 0 L -20 0 Q -15 -10 -10 0 Q -5 -10 0 0 Q 5 -10 10 0 Q 15 -10 20 0 L 30 0',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -30, y: 0, label: '1', direction: 'left' },
    { x: 30, y: 0, label: '2', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: true,
}

/**
 * Diode symbol
 */
export const diode: SymbolDefinition = {
  id: 'diode',
  name: 'Diode',
  width: 40,
  height: 24,
  paths: [
    // Triangle (anode)
    {
      d: 'M -20 0 L -8 0 L -8 -10 L 8 0 L -8 10 L -8 0',
      strokeWidth: 2,
      fill: 'none',
    },
    // Bar (cathode)
    {
      d: 'M 8 -10 L 8 10 M 8 0 L 20 0',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: 0, label: 'A', direction: 'left' },
    { x: 20, y: 0, label: 'K', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * LED symbol - diode with emission arrows
 */
export const led: SymbolDefinition = {
  id: 'led',
  name: 'LED',
  width: 40,
  height: 30,
  paths: [
    // Diode base
    {
      d: 'M -20 0 L -8 0 L -8 -10 L 8 0 L -8 10 L -8 0 M 8 -10 L 8 10 M 8 0 L 20 0',
      strokeWidth: 2,
    },
    // Emission arrows
    {
      d: 'M 2 -14 L 8 -20 M 5 -20 L 8 -20 L 8 -17 M 8 -14 L 14 -20 M 11 -20 L 14 -20 L 14 -17',
      strokeWidth: 1.5,
    },
  ],
  pins: [
    { x: -20, y: 0, label: 'A', direction: 'left' },
    { x: 20, y: 0, label: 'K', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * Zener diode symbol
 */
export const zenerDiode: SymbolDefinition = {
  id: 'zener',
  name: 'Zener Diode',
  width: 40,
  height: 24,
  paths: [
    // Triangle
    {
      d: 'M -20 0 L -8 0 L -8 -10 L 8 0 L -8 10 L -8 0',
      strokeWidth: 2,
    },
    // Bar with bent ends
    {
      d: 'M 4 -10 L 8 -10 L 8 10 L 12 10 M 8 0 L 20 0',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: 0, label: 'A', direction: 'left' },
    { x: 20, y: 0, label: 'K', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * NPN transistor symbol
 */
export const npnTransistor: SymbolDefinition = {
  id: 'npn',
  name: 'NPN Transistor',
  width: 40,
  height: 50,
  paths: [
    // Vertical bar (base region)
    {
      d: 'M 0 -15 L 0 15',
      strokeWidth: 3,
    },
    // Base lead
    {
      d: 'M -20 0 L 0 0',
      strokeWidth: 2,
    },
    // Collector
    {
      d: 'M 0 -8 L 15 -20',
      strokeWidth: 2,
    },
    // Emitter with arrow
    {
      d: 'M 0 8 L 15 20',
      strokeWidth: 2,
    },
    // Arrow on emitter
    {
      d: 'M 9 18 L 15 20 L 13 14',
      strokeWidth: 2,
    },
    // Leads
    {
      d: 'M 15 -20 L 15 -25 M 15 20 L 15 25',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: 0, label: 'B', direction: 'left' },
    { x: 15, y: -25, label: 'C', direction: 'up' },
    { x: 15, y: 25, label: 'E', direction: 'down' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * PNP transistor symbol
 */
export const pnpTransistor: SymbolDefinition = {
  id: 'pnp',
  name: 'PNP Transistor',
  width: 40,
  height: 50,
  paths: [
    // Vertical bar (base region)
    {
      d: 'M 0 -15 L 0 15',
      strokeWidth: 3,
    },
    // Base lead
    {
      d: 'M -20 0 L 0 0',
      strokeWidth: 2,
    },
    // Collector
    {
      d: 'M 0 -8 L 15 -20',
      strokeWidth: 2,
    },
    // Emitter with arrow (pointing in)
    {
      d: 'M 0 8 L 15 20',
      strokeWidth: 2,
    },
    // Arrow pointing toward base
    {
      d: 'M 2 10 L 0 8 L 4 6',
      strokeWidth: 2,
    },
    // Leads
    {
      d: 'M 15 -20 L 15 -25 M 15 20 L 15 25',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: 0, label: 'B', direction: 'left' },
    { x: 15, y: -25, label: 'C', direction: 'up' },
    { x: 15, y: 25, label: 'E', direction: 'down' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * N-channel MOSFET symbol
 */
export const nmosfet: SymbolDefinition = {
  id: 'nmosfet',
  name: 'N-MOSFET',
  width: 50,
  height: 50,
  paths: [
    // Gate vertical line
    {
      d: 'M -5 -15 L -5 15',
      strokeWidth: 2,
    },
    // Gate lead
    {
      d: 'M -20 0 L -8 0 M -8 -12 L -8 12',
      strokeWidth: 2,
    },
    // Channel segments
    {
      d: 'M 0 -15 L 0 -8 M 0 -4 L 0 4 M 0 8 L 0 15',
      strokeWidth: 3,
    },
    // Drain
    {
      d: 'M 0 -15 L 15 -15 L 15 -25',
      strokeWidth: 2,
    },
    // Source
    {
      d: 'M 0 15 L 15 15 L 15 25',
      strokeWidth: 2,
    },
    // Body connection and arrow
    {
      d: 'M 0 0 L 15 0 L 15 15',
      strokeWidth: 2,
    },
    // Arrow pointing in (N-channel)
    {
      d: 'M 6 3 L 0 0 L 6 -3',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: 0, label: 'G', direction: 'left' },
    { x: 15, y: -25, label: 'D', direction: 'up' },
    { x: 15, y: 25, label: 'S', direction: 'down' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * P-channel MOSFET symbol
 */
export const pmosfet: SymbolDefinition = {
  id: 'pmosfet',
  name: 'P-MOSFET',
  width: 50,
  height: 50,
  paths: [
    // Gate vertical line
    {
      d: 'M -5 -15 L -5 15',
      strokeWidth: 2,
    },
    // Gate lead
    {
      d: 'M -20 0 L -8 0 M -8 -12 L -8 12',
      strokeWidth: 2,
    },
    // Channel segments
    {
      d: 'M 0 -15 L 0 -8 M 0 -4 L 0 4 M 0 8 L 0 15',
      strokeWidth: 3,
    },
    // Drain
    {
      d: 'M 0 -15 L 15 -15 L 15 -25',
      strokeWidth: 2,
    },
    // Source
    {
      d: 'M 0 15 L 15 15 L 15 25',
      strokeWidth: 2,
    },
    // Body connection and arrow
    {
      d: 'M 0 0 L 15 0 L 15 15',
      strokeWidth: 2,
    },
    // Arrow pointing out (P-channel)
    {
      d: 'M 9 3 L 15 0 L 9 -3',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: 0, label: 'G', direction: 'left' },
    { x: 15, y: -25, label: 'D', direction: 'up' },
    { x: 15, y: 25, label: 'S', direction: 'down' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * Generic IC symbol - rectangular with pins
 */
export const genericIC: SymbolDefinition = {
  id: 'ic',
  name: 'IC',
  width: 80,
  height: 100,
  paths: [
    // Rectangle body
    {
      d: 'M -30 -40 L 30 -40 L 30 40 L -30 40 L -30 -40',
      strokeWidth: 2,
    },
    // Notch/dot for pin 1 orientation
    {
      d: 'M -30 -35 Q -25 -40 -20 -35',
      strokeWidth: 2,
    },
  ],
  pins: [
    // Left side pins
    { x: -40, y: -30, label: '1', direction: 'left' },
    { x: -40, y: -10, label: '2', direction: 'left' },
    { x: -40, y: 10, label: '3', direction: 'left' },
    { x: -40, y: 30, label: '4', direction: 'left' },
    // Right side pins
    { x: 40, y: -30, label: '8', direction: 'right' },
    { x: 40, y: -10, label: '7', direction: 'right' },
    { x: 40, y: 10, label: '6', direction: 'right' },
    { x: 40, y: 30, label: '5', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * Fuse symbol
 */
export const fuse: SymbolDefinition = {
  id: 'fuse',
  name: 'Fuse',
  width: 50,
  height: 16,
  paths: [
    // Rectangle with wavy line inside
    {
      d: 'M -25 0 L -15 0 M -15 -6 L 15 -6 L 15 6 L -15 6 L -15 -6 M 15 0 L 25 0',
      strokeWidth: 2,
    },
    // Wavy element inside
    {
      d: 'M -10 0 Q -5 -3 0 0 Q 5 3 10 0',
      strokeWidth: 1.5,
    },
  ],
  pins: [
    { x: -25, y: 0, label: '1', direction: 'left' },
    { x: 25, y: 0, label: '2', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: true,
}

/**
 * Ground symbol
 */
export const ground: SymbolDefinition = {
  id: 'ground',
  name: 'Ground',
  width: 30,
  height: 20,
  paths: [
    {
      d: 'M 0 -10 L 0 0 M -12 0 L 12 0 M -8 5 L 8 5 M -4 10 L 4 10',
      strokeWidth: 2,
    },
  ],
  pins: [{ x: 0, y: -10, label: 'GND', direction: 'up' }],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * Power/VCC symbol
 */
export const power: SymbolDefinition = {
  id: 'power',
  name: 'Power',
  width: 30,
  height: 20,
  paths: [
    {
      d: 'M 0 10 L 0 0 M -10 0 L 0 -10 L 10 0',
      strokeWidth: 2,
    },
  ],
  pins: [{ x: 0, y: 10, label: 'VCC', direction: 'down' }],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: true,
}

/**
 * Wire junction symbol (dot)
 */
export const junction: SymbolDefinition = {
  id: 'junction',
  name: 'Junction',
  width: 10,
  height: 10,
  paths: [
    {
      d: 'M 0 -4 A 4 4 0 1 1 0 4 A 4 4 0 1 1 0 -4',
      strokeWidth: 0,
      fill: 'currentColor',
    },
  ],
  pins: [{ x: 0, y: 0, label: '', direction: 'left' }],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * Switch symbol (SPST)
 */
export const switchSPST: SymbolDefinition = {
  id: 'switch',
  name: 'Switch',
  width: 50,
  height: 20,
  paths: [
    // Fixed contacts
    {
      d: 'M -25 0 L -10 0 M 10 0 L 25 0',
      strokeWidth: 2,
    },
    // Contact circles
    {
      d: 'M -10 0 A 2 2 0 1 1 -10 0.1 M 10 0 A 2 2 0 1 1 10 0.1',
      strokeWidth: 2,
    },
    // Movable arm
    {
      d: 'M -8 0 L 6 -10',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -25, y: 0, label: '1', direction: 'left' },
    { x: 25, y: 0, label: '2', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * Connector symbol
 */
export const connector: SymbolDefinition = {
  id: 'connector',
  name: 'Connector',
  width: 40,
  height: 60,
  paths: [
    // Connector body
    {
      d: 'M -15 -25 L 15 -25 L 15 25 L -15 25 L -15 -25',
      strokeWidth: 2,
    },
    // Pin markers
    {
      d: 'M -15 -15 L -5 -15 M -15 0 L -5 0 M -15 15 L -5 15',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: -15, label: '1', direction: 'left' },
    { x: -20, y: 0, label: '2', direction: 'left' },
    { x: -20, y: 15, label: '3', direction: 'left' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: false,
}

/**
 * Crystal/oscillator symbol
 */
export const crystal: SymbolDefinition = {
  id: 'crystal',
  name: 'Crystal',
  width: 40,
  height: 24,
  paths: [
    // Plates
    {
      d: 'M -20 0 L -8 0 M -8 -10 L -8 10 M 8 -10 L 8 10 M 8 0 L 20 0',
      strokeWidth: 2,
    },
    // Crystal body
    {
      d: 'M -5 -8 L 5 -8 L 5 8 L -5 8 L -5 -8',
      strokeWidth: 2,
    },
  ],
  pins: [
    { x: -20, y: 0, label: '1', direction: 'left' },
    { x: 20, y: 0, label: '2', direction: 'right' },
  ],
  defaultOrientation: 0,
  standard: 'ieee',
  hasValueLabel: true,
}
