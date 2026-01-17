/**
 * Pin position on a symbol
 */
export interface PinPosition {
  /** X coordinate relative to symbol center */
  x: number
  /** Y coordinate relative to symbol center */
  y: number
  /** Pin label (e.g., "1", "2", "VCC", "GND") */
  label: string
  /** Direction the wire exits (for routing) */
  direction: 'left' | 'right' | 'up' | 'down'
}

/**
 * Symbol orientation
 */
export type SymbolOrientation = 0 | 90 | 180 | 270

/**
 * Symbol standard (American/IEEE vs European/IEC)
 */
export type SymbolStandard = 'ieee' | 'iec'

/**
 * SVG path data for a symbol
 */
export interface SymbolPath {
  /** SVG path d attribute */
  d: string
  /** Stroke color (default: currentColor) */
  stroke?: string
  /** Fill color (default: none) */
  fill?: string
  /** Stroke width (default: 2) */
  strokeWidth?: number
}

/**
 * A schematic symbol definition
 */
export interface SymbolDefinition {
  /** Symbol identifier */
  id: string
  /** Display name */
  name: string
  /** Width of the symbol bounding box */
  width: number
  /** Height of the symbol bounding box */
  height: number
  /** SVG paths that make up the symbol */
  paths: SymbolPath[]
  /** Pin positions relative to center */
  pins: PinPosition[]
  /** Default orientation */
  defaultOrientation: SymbolOrientation
  /** Symbol standard this definition belongs to */
  standard: SymbolStandard
  /** Whether this symbol has a value label area */
  hasValueLabel: boolean
}

/**
 * Render context for symbols
 */
export interface SymbolRenderContext {
  /** X position on canvas */
  x: number
  /** Y position on canvas */
  y: number
  /** Rotation angle */
  orientation: SymbolOrientation
  /** Scale factor */
  scale: number
  /** Component reference (e.g., "R1", "U1") */
  reference: string
  /** Component value (e.g., "10k", "100nF") */
  value?: string
  /** Whether symbol is selected */
  selected: boolean
  /** Whether symbol is hovered */
  hovered: boolean
  /** Whether symbol is highlighted (in filter results) */
  highlighted: boolean
}

/**
 * Category of symbols
 */
export type SymbolCategory = 'passive' | 'semiconductor' | 'ic' | 'connector' | 'power' | 'misc'

/**
 * Symbol metadata for registry
 */
export interface SymbolMetadata {
  /** Symbol definition */
  definition: SymbolDefinition
  /** Component types this symbol matches */
  matchTypes: string[]
  /** Category */
  category: SymbolCategory
  /** Whether this is a default symbol for unknown types */
  isDefault?: boolean
}
