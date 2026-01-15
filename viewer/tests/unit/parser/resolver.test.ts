import { describe, it, expect } from 'vitest'
import { resolve, createMapLoader, getComponentTypes, getAllNets } from '@/parser/resolver'

describe('resolver', () => {
  describe('single file resolution', () => {
    it('should resolve a circuit without subcircuits', async () => {
      const content = `[VCC]: net
[U1]: esp32`
      const loader = createMapLoader(new Map())

      const result = await resolve(content, 'test.circuit.md', loader)

      expect(result.errors).toHaveLength(0)
      expect(result.ast.nets.size).toBe(1)
      expect(result.ast.components.size).toBe(1)
    })
  })

  describe('subcircuit resolution', () => {
    it('should resolve a simple subcircuit', async () => {
      const mainContent = `[VCC]: net
[PSU]: @./power.circuit.md
[PSU.VOUT --- VCC]`

      const powerContent = `[VOUT]: net
[GND]: net
[U1]: lm1117`

      const files = new Map([['power.circuit.md', powerContent]])
      const loader = createMapLoader(files)

      const result = await resolve(mainContent, 'main.circuit.md', loader)

      expect(result.errors).toHaveLength(0)
      expect(result.ast.subcircuits.size).toBe(1)

      const psu = result.ast.subcircuits.get('PSU')
      expect(psu?.resolved).toBeDefined()
      expect(psu?.resolved?.nets.size).toBe(2)
    })

    it('should resolve nested subcircuits', async () => {
      const mainContent = '[PSU]: @./power.circuit.md'
      const powerContent = '[REG]: @./regulator.circuit.md'
      const regulatorContent = '[U1]: lm1117'

      const files = new Map([
        ['power.circuit.md', powerContent],
        ['regulator.circuit.md', regulatorContent],
      ])
      const loader = createMapLoader(files)

      const result = await resolve(mainContent, 'main.circuit.md', loader)

      expect(result.errors).toHaveLength(0)

      const psu = result.ast.subcircuits.get('PSU')
      expect(psu?.resolved?.subcircuits.get('REG')?.resolved).toBeDefined()
    })

    it('should error on missing subcircuit', async () => {
      const content = '[PSU]: @./missing.circuit.md'
      const loader = createMapLoader(new Map())

      const result = await resolve(content, 'test.circuit.md', loader)

      expect(result.errors.length).toBeGreaterThan(0)
      expect(result.errors[0].message).toContain('not found')
    })

    it('should detect circular references', async () => {
      const aContent = '[B]: @./b.circuit.md'
      const bContent = '[A]: @./a.circuit.md'

      const files = new Map([
        ['a.circuit.md', aContent],
        ['b.circuit.md', bContent],
      ])
      const loader = createMapLoader(files)

      const result = await resolve(aContent, 'a.circuit.md', loader)

      expect(result.errors.some((e) => e.message.includes('Circular'))).toBe(true)
    })

    it('should respect max depth', async () => {
      // Create a chain of subcircuits
      const files = new Map<string, string>()
      for (let i = 0; i < 15; i++) {
        files.set(`level${i}.circuit.md`, `[NEXT]: @./level${i + 1}.circuit.md`)
      }
      files.set('level15.circuit.md', '[END]: net')

      const loader = createMapLoader(files)
      const result = await resolve(
        '[START]: @./level0.circuit.md',
        'main.circuit.md',
        loader,
        { maxDepth: 5 }
      )

      expect(result.errors.some((e) => e.message.includes('depth'))).toBe(true)
    })
  })

  describe('path resolution', () => {
    it('should resolve relative paths', async () => {
      const mainContent = '[SUB]: @./subdir/circuit.circuit.md'
      const subContent = '[NET]: net'

      const files = new Map([['subdir/circuit.circuit.md', subContent]])
      const loader = createMapLoader(files)

      const result = await resolve(mainContent, 'main.circuit.md', loader)

      expect(result.errors).toHaveLength(0)
      expect(result.files.has('subdir/circuit.circuit.md')).toBe(true)
    })
  })

  describe('utility functions', () => {
    it('should get all component types', async () => {
      const mainContent = `[U1]: esp32
[R1]: resistor(10k)
[VCC --- 100nF --- GND]
[SUB]: @./sub.circuit.md`

      const subContent = `[U2]: lm1117
[D1]: led`

      const files = new Map([['sub.circuit.md', subContent]])
      const loader = createMapLoader(files)

      const result = await resolve(mainContent, 'main.circuit.md', loader)
      const types = getComponentTypes(result.ast, true)

      expect(types.has('esp32')).toBe(true)
      expect(types.has('resistor')).toBe(true)
      expect(types.has('capacitor')).toBe(true) // From inline passive
      expect(types.has('lm1117')).toBe(true) // From subcircuit
      expect(types.has('led')).toBe(true) // From subcircuit
    })

    it('should get all nets', async () => {
      const mainContent = `[VCC]: net
[GND]: net
[SUB]: @./sub.circuit.md`

      const subContent = `[VOUT]: net
[EN]: net`

      const files = new Map([['sub.circuit.md', subContent]])
      const loader = createMapLoader(files)

      const result = await resolve(mainContent, 'main.circuit.md', loader)
      const nets = getAllNets(result.ast, true)

      expect(nets.has('VCC')).toBe(true)
      expect(nets.has('GND')).toBe(true)
      expect(nets.has('SUB.VOUT')).toBe(true)
      expect(nets.has('SUB.EN')).toBe(true)
    })
  })

  describe('lazy resolution', () => {
    it('should not resolve subcircuits when lazy is true', async () => {
      const mainContent = '[PSU]: @./power.circuit.md'
      const powerContent = '[U1]: lm1117'

      const files = new Map([['power.circuit.md', powerContent]])
      const loader = createMapLoader(files)

      const result = await resolve(mainContent, 'main.circuit.md', loader, { lazy: true })

      expect(result.errors).toHaveLength(0)
      const psu = result.ast.subcircuits.get('PSU')
      expect(psu?.resolved).toBeUndefined()
    })
  })
})
