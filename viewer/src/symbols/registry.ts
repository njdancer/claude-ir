import type { SymbolMetadata, SymbolStandard, SymbolCategory } from './types'
import {
  resistorIEEE,
  resistorIEC,
  capacitor,
  capacitorPolarized,
  inductor,
  diode,
  led,
  zenerDiode,
  npnTransistor,
  pnpTransistor,
  nmosfet,
  pmosfet,
  genericIC,
  fuse,
  ground,
  power,
  junction,
  switchSPST,
  connector,
  crystal,
} from './definitions'

/**
 * Symbol registry holds all available symbols and manages standard selection
 */
export interface SymbolRegistry {
  /** All registered symbols by ID */
  symbols: Map<string, SymbolMetadata>
  /** Type to symbol ID mapping (lowercase type -> symbol ID) */
  typeMap: Map<string, string[]>
  /** Current symbol standard */
  standard: SymbolStandard
}

/**
 * Create a new symbol registry with all default symbols
 */
export function createSymbolRegistry(): SymbolRegistry {
  const registry: SymbolRegistry = {
    symbols: new Map(),
    typeMap: new Map(),
    standard: 'ieee',
  }

  // Register passive components
  registerSymbol(registry, {
    definition: resistorIEEE,
    matchTypes: ['resistor', 'res', 'r'],
    category: 'passive',
  })

  registerSymbol(registry, {
    definition: resistorIEC,
    matchTypes: ['resistor', 'res', 'r'],
    category: 'passive',
  })

  registerSymbol(registry, {
    definition: capacitor,
    matchTypes: ['capacitor', 'cap', 'c'],
    category: 'passive',
  })

  registerSymbol(registry, {
    definition: capacitorPolarized,
    matchTypes: ['electrolytic', 'polarized-cap', 'elec'],
    category: 'passive',
  })

  registerSymbol(registry, {
    definition: inductor,
    matchTypes: ['inductor', 'ind', 'l', 'coil'],
    category: 'passive',
  })

  registerSymbol(registry, {
    definition: fuse,
    matchTypes: ['fuse', 'ptc', 'polyfuse'],
    category: 'passive',
  })

  registerSymbol(registry, {
    definition: crystal,
    matchTypes: ['crystal', 'xtal', 'oscillator', 'osc'],
    category: 'passive',
  })

  // Register semiconductors
  registerSymbol(registry, {
    definition: diode,
    matchTypes: ['diode', 'd', '1n4148', '1n4001'],
    category: 'semiconductor',
  })

  registerSymbol(registry, {
    definition: led,
    matchTypes: ['led', 'light-emitting-diode'],
    category: 'semiconductor',
  })

  registerSymbol(registry, {
    definition: zenerDiode,
    matchTypes: ['zener', 'tvs', 'suppressor'],
    category: 'semiconductor',
  })

  registerSymbol(registry, {
    definition: npnTransistor,
    matchTypes: ['npn', 'bjt-npn', '2n2222', '2n3904', 'bc547'],
    category: 'semiconductor',
  })

  registerSymbol(registry, {
    definition: pnpTransistor,
    matchTypes: ['pnp', 'bjt-pnp', '2n2907', '2n3906', 'bc557'],
    category: 'semiconductor',
  })

  registerSymbol(registry, {
    definition: nmosfet,
    matchTypes: ['nmos', 'n-mosfet', 'nfet', 'n-channel', '2n7000', 'bss138', 'irlz44n'],
    category: 'semiconductor',
  })

  registerSymbol(registry, {
    definition: pmosfet,
    matchTypes: ['pmos', 'p-mosfet', 'pfet', 'p-channel', 'irf9540'],
    category: 'semiconductor',
  })

  // Register ICs
  registerSymbol(registry, {
    definition: genericIC,
    matchTypes: [],
    category: 'ic',
    isDefault: true,
  })

  // Register connectors
  registerSymbol(registry, {
    definition: connector,
    matchTypes: ['connector', 'header', 'pin-header', 'jack'],
    category: 'connector',
  })

  registerSymbol(registry, {
    definition: switchSPST,
    matchTypes: ['switch', 'spst', 'button', 'sw'],
    category: 'connector',
  })

  // Register power symbols
  registerSymbol(registry, {
    definition: ground,
    matchTypes: ['ground', 'gnd'],
    category: 'power',
  })

  registerSymbol(registry, {
    definition: power,
    matchTypes: ['power', 'vcc', 'vdd', 'supply'],
    category: 'power',
  })

  registerSymbol(registry, {
    definition: junction,
    matchTypes: ['junction', 'node', 'connection'],
    category: 'misc',
  })

  return registry
}

/**
 * Register a symbol in the registry
 */
function registerSymbol(registry: SymbolRegistry, metadata: SymbolMetadata): void {
  registry.symbols.set(metadata.definition.id, metadata)

  // Add type mappings
  for (const type of metadata.matchTypes) {
    const key = type.toLowerCase()
    if (!registry.typeMap.has(key)) {
      registry.typeMap.set(key, [])
    }
    registry.typeMap.get(key)!.push(metadata.definition.id)
  }
}

/**
 * Get symbol for a component type
 */
export function getSymbolForType(registry: SymbolRegistry, componentType: string): SymbolMetadata | undefined {
  const key = componentType.toLowerCase()
  const symbolIds = registry.typeMap.get(key)

  if (symbolIds && symbolIds.length > 0) {
    // Find symbol matching current standard preference
    for (const id of symbolIds) {
      const metadata = registry.symbols.get(id)
      if (metadata) {
        // For components with standard variants (like resistors), prefer current standard
        if (metadata.definition.standard === registry.standard) {
          return metadata
        }
      }
    }
    // If no exact standard match, return first available
    return registry.symbols.get(symbolIds[0])
  }

  // Return default IC symbol for unknown types
  for (const metadata of registry.symbols.values()) {
    if (metadata.isDefault) {
      return metadata
    }
  }

  return undefined
}

/**
 * Get all symbols in a category
 */
export function getSymbolsByCategory(registry: SymbolRegistry, category: SymbolCategory): SymbolMetadata[] {
  const result: SymbolMetadata[] = []
  for (const metadata of registry.symbols.values()) {
    if (metadata.category === category) {
      result.push(metadata)
    }
  }
  return result
}

/**
 * Set the symbol standard (IEEE or IEC)
 */
export function setSymbolStandard(registry: SymbolRegistry, standard: SymbolStandard): void {
  registry.standard = standard
}

/**
 * Get the current symbol standard
 */
export function getSymbolStandard(registry: SymbolRegistry): SymbolStandard {
  return registry.standard
}

/**
 * Get a symbol by its ID
 */
export function getSymbolById(registry: SymbolRegistry, id: string): SymbolMetadata | undefined {
  return registry.symbols.get(id)
}

/**
 * List all registered symbol IDs
 */
export function getAllSymbolIds(registry: SymbolRegistry): string[] {
  return Array.from(registry.symbols.keys())
}
