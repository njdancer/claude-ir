import { describe, it, expect, beforeEach } from 'vitest'
import {
  SymbolRegistry,
  createSymbolRegistry,
  getSymbolForType,
  getSymbolsByCategory,
  setSymbolStandard,
  getSymbolStandard,
} from '@/symbols/registry'

describe('symbol registry', () => {
  let registry: SymbolRegistry

  beforeEach(() => {
    registry = createSymbolRegistry()
  })

  describe('createSymbolRegistry', () => {
    it('should create a registry with default symbols', () => {
      expect(registry).toBeDefined()
      expect(registry.symbols.size).toBeGreaterThan(0)
    })

    it('should have default standard set to IEEE', () => {
      expect(getSymbolStandard(registry)).toBe('ieee')
    })
  })

  describe('getSymbolForType', () => {
    it('should return resistor symbol for resistor type', () => {
      const symbol = getSymbolForType(registry, 'resistor')
      expect(symbol).toBeDefined()
      expect(symbol?.definition.id).toMatch(/resistor/i)
    })

    it('should return capacitor symbol for capacitor type', () => {
      const symbol = getSymbolForType(registry, 'capacitor')
      expect(symbol).toBeDefined()
      expect(symbol?.definition.id).toMatch(/capacitor/i)
    })

    it('should return inductor symbol for inductor type', () => {
      const symbol = getSymbolForType(registry, 'inductor')
      expect(symbol).toBeDefined()
    })

    it('should return diode symbol for diode type', () => {
      const symbol = getSymbolForType(registry, 'diode')
      expect(symbol).toBeDefined()
    })

    it('should return LED symbol for led type', () => {
      const symbol = getSymbolForType(registry, 'led')
      expect(symbol).toBeDefined()
    })

    it('should return transistor symbol for npn type', () => {
      const symbol = getSymbolForType(registry, 'npn')
      expect(symbol).toBeDefined()
    })

    it('should return MOSFET symbol for nmos/n-mosfet type', () => {
      const symbol = getSymbolForType(registry, 'nmos')
      expect(symbol).toBeDefined()

      const symbol2 = getSymbolForType(registry, 'n-mosfet')
      expect(symbol2).toBeDefined()
    })

    it('should return generic IC symbol for unknown component types', () => {
      const symbol = getSymbolForType(registry, 'esp32')
      expect(symbol).toBeDefined()
      expect(symbol?.definition.id).toMatch(/ic/i)
    })

    it('should return generic IC for any unknown type', () => {
      const symbol = getSymbolForType(registry, 'unknown_component_xyz')
      expect(symbol).toBeDefined()
    })
  })

  describe('symbol standard toggle', () => {
    it('should switch to IEC standard', () => {
      setSymbolStandard(registry, 'iec')
      expect(getSymbolStandard(registry)).toBe('iec')
    })

    it('should return IEC resistor when standard is IEC', () => {
      setSymbolStandard(registry, 'iec')
      const symbol = getSymbolForType(registry, 'resistor')
      expect(symbol?.definition.standard).toBe('iec')
    })

    it('should return IEEE resistor when standard is IEEE', () => {
      setSymbolStandard(registry, 'ieee')
      const symbol = getSymbolForType(registry, 'resistor')
      expect(symbol?.definition.standard).toBe('ieee')
    })
  })

  describe('getSymbolsByCategory', () => {
    it('should return passive symbols', () => {
      const passives = getSymbolsByCategory(registry, 'passive')
      expect(passives.length).toBeGreaterThan(0)
      expect(passives.every((s) => s.category === 'passive')).toBe(true)
    })

    it('should return semiconductor symbols', () => {
      const semiconductors = getSymbolsByCategory(registry, 'semiconductor')
      expect(semiconductors.length).toBeGreaterThan(0)
    })

    it('should return power symbols', () => {
      const power = getSymbolsByCategory(registry, 'power')
      expect(power.length).toBeGreaterThan(0)
    })
  })

  describe('case insensitivity', () => {
    it('should find symbols regardless of case', () => {
      expect(getSymbolForType(registry, 'RESISTOR')).toBeDefined()
      expect(getSymbolForType(registry, 'Capacitor')).toBeDefined()
      expect(getSymbolForType(registry, 'LED')).toBeDefined()
    })
  })
})
