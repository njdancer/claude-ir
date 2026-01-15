import { describe, it, expect } from 'vitest'
import { buildGraph } from '@/graph/builder'
import { parse } from '@/parser'

describe('graph builder', () => {
  describe('node creation', () => {
    it('should create nodes for nets', () => {
      const ast = parse('[VCC]: net\n[GND]: net', 'test.circuit.md')
      const graph = buildGraph(ast)

      expect(graph.nodes.size).toBe(2)
      expect(graph.nodes.has('net:VCC')).toBe(true)
      expect(graph.nodes.has('net:GND')).toBe(true)

      const vcc = graph.nodes.get('net:VCC')
      expect(vcc?.type).toBe('net')
      if (vcc?.type === 'net') {
        expect(vcc.name).toBe('VCC')
      }
    })

    it('should create nodes for components', () => {
      const ast = parse('[U1]: esp32_wroom(4MB)', 'test.circuit.md')
      const graph = buildGraph(ast)

      expect(graph.nodes.has('comp:U1')).toBe(true)
      const u1 = graph.nodes.get('comp:U1')
      if (u1?.type === 'component') {
        expect(u1.ref).toBe('U1')
        expect(u1.componentType).toBe('esp32_wroom')
        expect(u1.params).toEqual(['4MB'])
      }
    })

    it('should create nodes for subcircuits', () => {
      const ast = parse('[PSU]: @./power.circuit.md', 'test.circuit.md')
      const graph = buildGraph(ast)

      expect(graph.nodes.has('sub:PSU')).toBe(true)
      const psu = graph.nodes.get('sub:PSU')
      if (psu?.type === 'subcircuit') {
        expect(psu.ref).toBe('PSU')
        expect(psu.path).toBe('./power.circuit.md')
      }
    })

    it('should create nodes for inline passives', () => {
      const ast = parse('[VCC --- 10kΩ --- GND]', 'test.circuit.md')
      const graph = buildGraph(ast)

      // Should have: net VCC, net GND, inline passive
      expect(graph.nodes.has('passive:_R1')).toBe(true)
      const r1 = graph.nodes.get('passive:_R1')
      if (r1?.type === 'inline_passive') {
        expect(r1.passiveType).toBe('resistor')
        expect(r1.value).toBe('10kΩ')
      }
    })

    it('should detect power nets', () => {
      const ast = parse(
        `[VCC]: net
[GND]: net
[VDD]: net
[VSS]: net
[VBUS]: net
[SDA]: net`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)

      expect((graph.nodes.get('net:VCC') as { isPower: boolean }).isPower).toBe(true)
      expect((graph.nodes.get('net:GND') as { isPower: boolean }).isPower).toBe(true)
      expect((graph.nodes.get('net:VDD') as { isPower: boolean }).isPower).toBe(true)
      expect((graph.nodes.get('net:VSS') as { isPower: boolean }).isPower).toBe(true)
      expect((graph.nodes.get('net:VBUS') as { isPower: boolean }).isPower).toBe(true)
      expect((graph.nodes.get('net:SDA') as { isPower: boolean }).isPower).toBe(false)
    })
  })

  describe('edge creation', () => {
    it('should create edges for connections', () => {
      const ast = parse(
        `[VCC]: net
[U1]: esp32
[U1.VCC --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)

      expect(graph.edges.length).toBe(1)
      const edge = graph.edges[0]
      expect(edge.sourceId).toBe('comp:U1')
      expect(edge.sourcePin).toBe('VCC')
      expect(edge.targetId).toBe('net:VCC')
    })

    it('should create edges for inline passives', () => {
      const ast = parse('[VCC --- 10kΩ --- U1.RESET]', 'test.circuit.md')
      const graph = buildGraph(ast)

      // Should create 2 edges: VCC -> _R1, _R1 -> U1.RESET
      expect(graph.edges.length).toBe(2)
    })

    it('should handle numbered pins', () => {
      const ast = parse(
        `[VCC]: net
[R1]: resistor(10k)
[R1#1 --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)

      const edge = graph.edges[0]
      expect(edge.sourceId).toBe('comp:R1')
      expect(edge.sourcePin).toBe('1')
    })
  })

  describe('pin tracking', () => {
    it('should track pins used on components', () => {
      const ast = parse(
        `[U1]: esp32
[U1.VCC --- VCC]
[U1.GND --- GND]
[U1.GPIO0 --- SIG]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)

      const u1 = graph.nodes.get('comp:U1')
      if (u1?.type === 'component') {
        expect(u1.pins).toContain('VCC')
        expect(u1.pins).toContain('GND')
        expect(u1.pins).toContain('GPIO0')
      }
    })
  })

  describe('metadata', () => {
    it('should include frontmatter metadata', () => {
      const ast = parse(
        `---
name: Test Circuit
description: A test
---
[VCC]: net`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)

      expect(graph.metadata.name).toBe('Test Circuit')
      expect(graph.metadata.description).toBe('A test')
    })
  })

  describe('full circuit', () => {
    it('should build graph for a complete circuit', () => {
      const ast = parse(
        `---
name: Power Supply
---
[VIN]: net
[VOUT]: net
[GND]: net

[U1]: lm1117(3.3V)
[PSU]: @./buck.circuit.md

[VIN --- U1.VIN]
[U1.VOUT --- VOUT]
[U1.GND --- GND]

[VIN --- 10µF --- GND]
[VOUT --- 100nF --- GND]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)

      // 3 nets + 1 component + 1 subcircuit + 2 inline passives = 7 nodes
      expect(graph.nodes.size).toBe(7)
      // 3 direct connections + 2*2 inline passive connections = 7 edges
      expect(graph.edges.length).toBe(7)
    })
  })
})
