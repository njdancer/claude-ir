import { describe, it, expect } from 'vitest'
import { layoutGraphElk } from '@/layout/elk-layout'
import type { CircuitGraph, ComponentGraphNode, NetGraphNode } from '@/graph'

/**
 * Create a simple test graph
 */
function createTestGraph(): CircuitGraph {
  const nodes = new Map<string, ComponentGraphNode | NetGraphNode>()

  // Add components
  nodes.set('R1', {
    id: 'R1',
    type: 'component',
    label: 'R1',
    ref: 'R1',
    componentType: 'resistor',
    params: ['10kΩ'],
    pins: ['1', '2'],
    metadata: {},
  })

  nodes.set('C1', {
    id: 'C1',
    type: 'component',
    label: 'C1',
    ref: 'C1',
    componentType: 'capacitor',
    params: ['100nF'],
    pins: ['1', '2'],
    metadata: {},
  })

  // Add net
  nodes.set('VCC', {
    id: 'VCC',
    type: 'net',
    label: 'VCC',
    name: 'VCC',
    isPower: true,
    metadata: {},
  })

  return {
    nodes,
    edges: [
      { id: 'e1', sourceId: 'R1', sourcePin: '1', targetId: 'VCC', targetPin: undefined },
      { id: 'e2', sourceId: 'R1', sourcePin: '2', targetId: 'C1', targetPin: '1' },
    ],
    filename: 'test.circuit.md',
    metadata: { name: 'Test Circuit' },
  }
}

describe('ELK Layout', () => {
  it('should handle empty graph', async () => {
    const emptyGraph: CircuitGraph = {
      nodes: new Map(),
      edges: [],
      filename: 'empty.circuit.md',
      metadata: {},
    }

    const result = await layoutGraphElk(emptyGraph)

    expect(result.nodes.size).toBe(0)
    expect(result.edges).toHaveLength(0)
    expect(result.converged).toBe(true)
  })

  it('should layout a simple graph', async () => {
    const graph = createTestGraph()
    const result = await layoutGraphElk(graph)

    // Should have all nodes positioned
    expect(result.nodes.size).toBe(3)
    expect(result.nodes.has('R1')).toBe(true)
    expect(result.nodes.has('C1')).toBe(true)
    expect(result.nodes.has('VCC')).toBe(true)

    // All nodes should have valid positions
    for (const node of result.nodes.values()) {
      expect(typeof node.position.x).toBe('number')
      expect(typeof node.position.y).toBe('number')
      expect(isFinite(node.position.x)).toBe(true)
      expect(isFinite(node.position.y)).toBe(true)
    }
  })

  it('should route edges', async () => {
    const graph = createTestGraph()
    const result = await layoutGraphElk(graph)

    // Should have edges routed
    expect(result.edges.length).toBe(2)

    // Each edge should have waypoints
    for (const edge of result.edges) {
      expect(edge.waypoints.length).toBeGreaterThan(0)
      for (const waypoint of edge.waypoints) {
        expect(typeof waypoint.x).toBe('number')
        expect(typeof waypoint.y).toBe('number')
      }
    }
  })

  it('should calculate bounds', async () => {
    const graph = createTestGraph()
    const result = await layoutGraphElk(graph)

    // Bounds should encompass all nodes
    expect(result.bounds.width).toBeGreaterThan(0)
    expect(result.bounds.height).toBeGreaterThan(0)
  })

  it('should respect layout direction option', async () => {
    const graph = createTestGraph()

    const rightLayout = await layoutGraphElk(graph, { direction: 'RIGHT' })
    const downLayout = await layoutGraphElk(graph, { direction: 'DOWN' })

    // Different directions should produce different layouts
    const r1Right = rightLayout.nodes.get('R1')!
    const r1Down = downLayout.nodes.get('R1')!

    // The positions or bounds should differ
    const rightWidth = rightLayout.bounds.width
    const rightHeight = rightLayout.bounds.height
    const downWidth = downLayout.bounds.width
    const downHeight = downLayout.bounds.height

    // For RIGHT direction, typically wider than tall
    // For DOWN direction, typically taller than wide
    // (though this depends on graph structure)
    expect(rightWidth !== downWidth || rightHeight !== downHeight).toBe(true)
  })

  it('should handle nodes without connections', async () => {
    const graph = createTestGraph()

    // Add an unconnected node
    graph.nodes.set('R2', {
      id: 'R2',
      type: 'component',
      label: 'R2',
      ref: 'R2',
      componentType: 'resistor',
      params: ['4.7kΩ'],
      pins: ['1', '2'],
      metadata: {},
    } as ComponentGraphNode)

    const result = await layoutGraphElk(graph)

    // Unconnected node should still be positioned
    expect(result.nodes.has('R2')).toBe(true)
    const r2 = result.nodes.get('R2')!
    expect(isFinite(r2.position.x)).toBe(true)
    expect(isFinite(r2.position.y)).toBe(true)
  })

  it('should handle graph with cycles', async () => {
    const graph = createTestGraph()

    // Add edge that creates a cycle
    graph.edges.push({
      id: 'e3',
      sourceId: 'C1',
      sourcePin: '2',
      targetId: 'VCC',
    })

    // Should not throw
    const result = await layoutGraphElk(graph)
    expect(result.nodes.size).toBe(3)
    expect(result.edges.length).toBe(3)
  })
})
