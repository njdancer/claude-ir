import { describe, it, expect } from 'vitest'
import {
  resistorIEEE,
  resistorIEC,
  capacitor,
  capacitorPolarized,
  inductor,
  diode,
  led,
  npnTransistor,
  nmosfet,
  genericIC,
  ground,
  power,
  junction,
} from '@/symbols/definitions'
import type { SymbolDefinition } from '@/symbols/types'

describe('symbol definitions', () => {
  describe('structure validation', () => {
    const validateSymbol = (symbol: SymbolDefinition) => {
      expect(symbol.id).toBeTruthy()
      expect(symbol.name).toBeTruthy()
      expect(symbol.width).toBeGreaterThan(0)
      expect(symbol.height).toBeGreaterThan(0)
      expect(symbol.paths.length).toBeGreaterThan(0)
      expect(symbol.pins.length).toBeGreaterThan(0)
      expect(['ieee', 'iec']).toContain(symbol.standard)
    }

    it('should have valid resistor IEEE symbol', () => {
      validateSymbol(resistorIEEE)
      expect(resistorIEEE.standard).toBe('ieee')
      expect(resistorIEEE.pins).toHaveLength(2)
    })

    it('should have valid resistor IEC symbol', () => {
      validateSymbol(resistorIEC)
      expect(resistorIEC.standard).toBe('iec')
      expect(resistorIEC.pins).toHaveLength(2)
    })

    it('should have valid capacitor symbol', () => {
      validateSymbol(capacitor)
      expect(capacitor.pins).toHaveLength(2)
    })

    it('should have valid polarized capacitor symbol', () => {
      validateSymbol(capacitorPolarized)
      expect(capacitorPolarized.pins).toHaveLength(2)
    })

    it('should have valid inductor symbol', () => {
      validateSymbol(inductor)
      expect(inductor.pins).toHaveLength(2)
    })

    it('should have valid diode symbol', () => {
      validateSymbol(diode)
      expect(diode.pins).toHaveLength(2)
    })

    it('should have valid LED symbol', () => {
      validateSymbol(led)
      expect(led.pins).toHaveLength(2)
    })

    it('should have valid NPN transistor symbol', () => {
      validateSymbol(npnTransistor)
      expect(npnTransistor.pins).toHaveLength(3) // B, C, E
    })

    it('should have valid N-MOSFET symbol', () => {
      validateSymbol(nmosfet)
      expect(nmosfet.pins).toHaveLength(3) // G, D, S
    })

    it('should have valid generic IC symbol', () => {
      validateSymbol(genericIC)
      expect(genericIC.pins.length).toBeGreaterThanOrEqual(2)
    })

    it('should have valid ground symbol', () => {
      validateSymbol(ground)
      expect(ground.pins).toHaveLength(1)
    })

    it('should have valid power symbol', () => {
      validateSymbol(power)
      expect(power.pins).toHaveLength(1)
    })

    it('should have valid junction symbol', () => {
      validateSymbol(junction)
      expect(junction.pins).toHaveLength(1)
    })
  })

  describe('pin positions', () => {
    it('should have pins with valid directions', () => {
      const validDirections = ['left', 'right', 'up', 'down']

      for (const pin of resistorIEEE.pins) {
        expect(validDirections).toContain(pin.direction)
      }
    })

    it('resistor should have opposing pins', () => {
      const leftPin = resistorIEEE.pins.find((p) => p.direction === 'left')
      const rightPin = resistorIEEE.pins.find((p) => p.direction === 'right')

      expect(leftPin).toBeDefined()
      expect(rightPin).toBeDefined()
    })

    it('transistor should have three distinct pins', () => {
      const pinLabels = npnTransistor.pins.map((p) => p.label)
      expect(new Set(pinLabels).size).toBe(3)
    })
  })

  describe('SVG paths', () => {
    it('should have valid SVG path data', () => {
      for (const path of resistorIEEE.paths) {
        expect(path.d).toBeTruthy()
        expect(path.d).toMatch(/^[MLHVCSQTAZmlhvcsqtaz0-9.,\s-]+$/)
      }
    })
  })
})
