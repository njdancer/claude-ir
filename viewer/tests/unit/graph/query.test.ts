import { describe, it, expect } from 'vitest'
import { buildGraph } from '@/graph/builder'
import {
  getAdjacentNodes,
  getNodesOnNet,
  bfsTraversal,
  filterByNets,
  filterByComponents,
  filterByNeighborhood,
  getGraphStats,
} from '@/graph/query'
import { parse } from '@/parser'

const TEST_CIRCUIT = `
[VCC]: net
[GND]: net
[SIG]: net

[U1]: mcu
[U2]: sensor
[R1]: resistor(10k)

[U1.VCC --- VCC]
[U1.GND --- GND]
[U1.OUT --- SIG]
[U2.VCC --- VCC]
[U2.GND --- GND]
[U2.IN --- SIG]
[R1#1 --- VCC]
[R1#2 --- SIG]
`

describe('graph query', () => {
  describe('getAdjacentNodes', () => {
    it('should return all adjacent nodes', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const adjacent = getAdjacentNodes(graph, 'net:VCC')
      expect(adjacent.has('comp:U1')).toBe(true)
      expect(adjacent.has('comp:U2')).toBe(true)
      expect(adjacent.has('comp:R1')).toBe(true)
    })

    it('should return empty set for isolated nodes', () => {
      const ast = parse('[UNUSED]: net', 'test.circuit.md')
      const graph = buildGraph(ast)

      const adjacent = getAdjacentNodes(graph, 'net:UNUSED')
      expect(adjacent.size).toBe(0)
    })
  })

  describe('getNodesOnNet', () => {
    it('should return all nodes connected to a net', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const nodes = getNodesOnNet(graph, 'VCC')
      expect(nodes.has('net:VCC')).toBe(true)
      expect(nodes.has('comp:U1')).toBe(true)
      expect(nodes.has('comp:U2')).toBe(true)
      expect(nodes.has('comp:R1')).toBe(true)
    })

    it('should return empty set for non-existent net', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const nodes = getNodesOnNet(graph, 'NONEXISTENT')
      expect(nodes.size).toBe(0)
    })
  })

  describe('bfsTraversal', () => {
    it('should return correct distances', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const distances = bfsTraversal(graph, 'comp:U1')

      expect(distances.get('comp:U1')).toBe(0)
      expect(distances.get('net:VCC')).toBe(1)
      expect(distances.get('comp:U2')).toBe(2) // U1 -> VCC -> U2
    })

    it('should respect depth limit', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const distances = bfsTraversal(graph, 'comp:U1', 1)

      expect(distances.has('comp:U1')).toBe(true)
      expect(distances.has('net:VCC')).toBe(true)
      expect(distances.has('comp:U2')).toBe(false) // depth 2, limited to 1
    })
  })

  describe('filterByNets', () => {
    it('should include all nodes on selected nets', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const result = filterByNets(graph, ['SIG'])

      expect(result.graph.nodes.has('net:SIG')).toBe(true)
      expect(result.graph.nodes.has('comp:U1')).toBe(true)
      expect(result.graph.nodes.has('comp:U2')).toBe(true)
      expect(result.graph.nodes.has('comp:R1')).toBe(true)
    })

    it('should handle multiple nets', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const result = filterByNets(graph, ['VCC', 'GND'])

      expect(result.graph.nodes.has('net:VCC')).toBe(true)
      expect(result.graph.nodes.has('net:GND')).toBe(true)
      expect(result.graph.nodes.has('comp:U1')).toBe(true)
      expect(result.graph.nodes.has('comp:U2')).toBe(true)
    })

    it('should track boundary nodes', () => {
      const ast = parse(
        `[A]: net
[B]: net
[U1]: ic
[U2]: ic
[U1.OUT --- A]
[U2.IN --- A]
[U2.OUT --- B]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)

      const result = filterByNets(graph, ['A'])

      // B is connected to U2 which is in the result, but B itself is not filtered
      expect(result.boundaryNodes.has('net:B')).toBe(true)
    })
  })

  describe('filterByComponents', () => {
    it('should include selected components and connected nets', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const result = filterByComponents(graph, ['U1'])

      expect(result.graph.nodes.has('comp:U1')).toBe(true)
      expect(result.graph.nodes.has('net:VCC')).toBe(true)
      expect(result.graph.nodes.has('net:GND')).toBe(true)
      expect(result.graph.nodes.has('net:SIG')).toBe(true)
      expect(result.graph.nodes.has('comp:U2')).toBe(false)
    })
  })

  describe('filterByNeighborhood', () => {
    it('should return nodes within specified depth', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const result = filterByNeighborhood(graph, 'U1', 1)

      expect(result.graph.nodes.has('comp:U1')).toBe(true)
      expect(result.graph.nodes.has('net:VCC')).toBe(true)
      expect(result.graph.nodes.has('net:GND')).toBe(true)
      expect(result.graph.nodes.has('net:SIG')).toBe(true)
      // U2 is at depth 2
      expect(result.graph.nodes.has('comp:U2')).toBe(false)
    })

    it('should return nodes at greater depth when specified', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const result = filterByNeighborhood(graph, 'U1', 2)

      expect(result.graph.nodes.has('comp:U1')).toBe(true)
      expect(result.graph.nodes.has('comp:U2')).toBe(true) // Now included at depth 2
      expect(result.graph.nodes.has('comp:R1')).toBe(true)
    })

    it('should handle non-existent center node', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const result = filterByNeighborhood(graph, 'NONEXISTENT', 2)

      expect(result.graph.nodes.size).toBe(0)
    })
  })

  describe('getGraphStats', () => {
    it('should return correct statistics', () => {
      const ast = parse(TEST_CIRCUIT, 'test.circuit.md')
      const graph = buildGraph(ast)

      const stats = getGraphStats(graph)

      expect(stats.netCount).toBe(3)
      expect(stats.componentCount).toBe(3)
      expect(stats.subcircuitCount).toBe(0)
      expect(stats.nodeCount).toBe(6)
      expect(stats.edgeCount).toBe(8)
    })
  })
})
