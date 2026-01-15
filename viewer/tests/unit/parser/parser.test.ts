import { describe, it, expect } from 'vitest'
import { parse } from '@/parser/parser'

describe('parser', () => {
  describe('frontmatter parsing', () => {
    it('should parse simple frontmatter', () => {
      const input = `---
name: Power Supply
description: Simple power supply
---
[VCC]: net`
      const ast = parse(input, 'test.circuit.md')

      expect(ast.frontmatter.name).toBe('Power Supply')
      expect(ast.frontmatter.description).toBe('Simple power supply')
    })

    it('should parse multiline description', () => {
      const input = `---
name: Test Circuit
description: |
  This is a multiline
  description for testing
---
[VCC]: net`
      const ast = parse(input, 'test.circuit.md')

      expect(ast.frontmatter.description).toContain('multiline')
      expect(ast.frontmatter.description).toContain('testing')
    })
  })

  describe('net parsing', () => {
    it('should parse net declarations', () => {
      const input = `[VCC]: net
[GND]: net`
      const ast = parse(input, 'test.circuit.md')

      expect(ast.nets.size).toBe(2)
      expect(ast.nets.has('VCC')).toBe(true)
      expect(ast.nets.has('GND')).toBe(true)
    })

    it('should warn on duplicate net declarations', () => {
      const input = `[VCC]: net
[VCC]: net`
      const ast = parse(input, 'test.circuit.md')

      expect(ast.errors.length).toBeGreaterThan(0)
      expect(ast.errors[0].message).toContain('Duplicate')
    })
  })

  describe('component parsing', () => {
    it('should parse component declarations', () => {
      const input = '[U1]: esp32_wroom(4MB)'
      const ast = parse(input, 'test.circuit.md')

      expect(ast.components.size).toBe(1)
      const comp = ast.components.get('U1')
      expect(comp?.componentType).toBe('esp32_wroom')
      expect(comp?.params).toEqual(['4MB'])
    })

    it('should error on duplicate reference designators', () => {
      const input = `[U1]: esp32
[U1]: atmega328`
      const ast = parse(input, 'test.circuit.md')

      expect(ast.errors.some((e) => e.severity === 'error')).toBe(true)
    })
  })

  describe('subcircuit parsing', () => {
    it('should parse subcircuit references', () => {
      const input = '[PSU]: @./power-supply.circuit.md'
      const ast = parse(input, 'test.circuit.md')

      expect(ast.subcircuits.size).toBe(1)
      const sub = ast.subcircuits.get('PSU')
      expect(sub?.path).toBe('./power-supply.circuit.md')
    })
  })

  describe('connection parsing', () => {
    it('should parse simple connections', () => {
      const input = '[U1.VCC --- VCC]'
      const ast = parse(input, 'test.circuit.md')

      expect(ast.connections.length).toBe(1)
      const conn = ast.connections[0]
      expect(conn.from.ref).toBe('U1')
      expect(conn.from.pin).toBe('VCC')
      expect(conn.to.ref).toBe('VCC')
    })

    it('should parse numbered pin connections', () => {
      const input = '[R1#1 --- U1.RESET]'
      const ast = parse(input, 'test.circuit.md')

      const conn = ast.connections[0]
      expect(conn.from.ref).toBe('R1')
      expect(conn.from.pin).toBe('1')
    })
  })

  describe('inline passive parsing', () => {
    it('should parse inline passives', () => {
      const input = '[VCC --- 10kΩ --- U1.RESET]'
      const ast = parse(input, 'test.circuit.md')

      expect(ast.inlinePassives.length).toBe(1)
      const passive = ast.inlinePassives[0]
      expect(passive.passiveType).toBe('resistor')
      expect(passive.value).toBe('10kΩ')
      expect(passive.ref).toBe('_R1')
    })

    it('should generate sequential references', () => {
      const input = `[VCC --- 10kΩ --- A]
[VCC --- 4.7kΩ --- B]
[VCC --- 100nF --- GND]`
      const ast = parse(input, 'test.circuit.md')

      expect(ast.inlinePassives.length).toBe(3)
      expect(ast.inlinePassives[0].ref).toBe('_R1')
      expect(ast.inlinePassives[1].ref).toBe('_R2')
      expect(ast.inlinePassives[2].ref).toBe('_C1')
    })
  })

  describe('property parsing', () => {
    it('should parse properties', () => {
      const input = '[dropout ==> 1.2V]'
      const ast = parse(input, 'test.circuit.md')

      expect(ast.properties.length).toBe(1)
      expect(ast.properties[0].key).toBe('dropout')
      expect(ast.properties[0].value).toBe('1.2V')
    })
  })

  describe('endpoint parsing', () => {
    it('should parse component.pin format', () => {
      const input = '[U1.VCC --- VCC]'
      const ast = parse(input, 'test.circuit.md')

      const conn = ast.connections[0]
      expect(conn.from.ref).toBe('U1')
      expect(conn.from.pin).toBe('VCC')
      expect(conn.from.raw).toBe('U1.VCC')
    })

    it('should parse component#pin format', () => {
      const input = '[R1#1 --- VCC]'
      const ast = parse(input, 'test.circuit.md')

      const conn = ast.connections[0]
      expect(conn.from.ref).toBe('R1')
      expect(conn.from.pin).toBe('1')
    })

    it('should parse plain net references', () => {
      const input = '[VCC --- GND]'
      const ast = parse(input, 'test.circuit.md')

      const conn = ast.connections[0]
      expect(conn.from.ref).toBe('VCC')
      expect(conn.from.pin).toBeUndefined()
    })
  })

  describe('full circuit parsing', () => {
    it('should parse a complete circuit', () => {
      const input = `---
name: Test Circuit
---

[VCC]: net
[GND]: net

[U1]: lm1117(3.3V)

[VIN --- U1.VIN]
[U1.VOUT --- VCC]
[U1.GND --- GND]

[VIN --- 10µF --- GND]
[VCC --- 100nF --- GND]`
      const ast = parse(input, 'test.circuit.md')

      expect(ast.frontmatter.name).toBe('Test Circuit')
      expect(ast.nets.size).toBe(2)
      expect(ast.components.size).toBe(1)
      expect(ast.connections.length).toBe(3)
      expect(ast.inlinePassives.length).toBe(2)
      expect(ast.errors.length).toBe(0)
    })
  })
})
