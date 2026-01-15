import { describe, it, expect } from 'vitest'
import { parse } from '@/parser'
import { buildGraph } from '@/graph'
import { layoutGraph, computeForces, routeEdges, calculateBounds } from '@/layout'
import type { PositionedNode, LayoutOptions } from '@/layout'

describe('layout', () => {
  describe('layoutGraph', () => {
    it('should position all nodes from graph', () => {
      const ast = parse(
        `[VCC]: net
[GND]: net
[U1]: esp32
[R1]: resistor(10k)
[U1.VCC --- VCC]
[U1.GND --- GND]
[U1.IO1 --- R1#1]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = layoutGraph(graph)

      // Should have positioned all nodes
      expect(result.nodes.size).toBe(graph.nodes.size)

      // All nodes should have valid positions
      for (const node of result.nodes.values()) {
        expect(typeof node.position.x).toBe('number')
        expect(typeof node.position.y).toBe('number')
        expect(isFinite(node.position.x)).toBe(true)
        expect(isFinite(node.position.y)).toBe(true)
      }
    })

    it('should route edges between nodes', () => {
      const ast = parse(
        `[VCC]: net
[U1]: esp32
[U1.VCC --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = layoutGraph(graph)

      expect(result.edges.length).toBeGreaterThan(0)

      for (const edge of result.edges) {
        expect(edge.waypoints.length).toBeGreaterThanOrEqual(2)
      }
    })

    it('should calculate bounds containing all nodes', () => {
      const ast = parse(
        `[U1]: esp32
[U2]: sensor
[U1.IO --- U2.IO]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = layoutGraph(graph)

      // Bounds should contain all nodes
      for (const node of result.nodes.values()) {
        expect(node.position.x).toBeGreaterThanOrEqual(result.bounds.x)
        expect(node.position.x).toBeLessThanOrEqual(result.bounds.x + result.bounds.width)
        expect(node.position.y).toBeGreaterThanOrEqual(result.bounds.y)
        expect(node.position.y).toBeLessThanOrEqual(result.bounds.y + result.bounds.height)
      }
    })

    it('should respect maxIterations option', () => {
      const ast = parse(
        `[U1]: esp32
[U2]: sensor`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const options: LayoutOptions = { maxIterations: 10 }
      const result = layoutGraph(graph, options)

      expect(result.iterations).toBeLessThanOrEqual(10)
    })

    it('should handle empty graph', () => {
      const ast = parse('', 'test.circuit.md')
      const graph = buildGraph(ast)
      const result = layoutGraph(graph)

      expect(result.nodes.size).toBe(0)
      expect(result.edges.length).toBe(0)
    })
  })

  describe('computeForces', () => {
    it('should compute repulsion between close nodes', () => {
      const nodes = new Map<string, PositionedNode>([
        [
          'a',
          {
            id: 'a',
            position: { x: 0, y: 0 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
        [
          'b',
          {
            id: 'b',
            position: { x: 10, y: 0 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
      ])

      const forces = computeForces(nodes, [], { repulsionStrength: 1000 })

      // Node a should be pushed left (negative x)
      expect(forces.get('a')!.x).toBeLessThan(0)
      // Node b should be pushed right (positive x)
      expect(forces.get('b')!.x).toBeGreaterThan(0)
    })

    it('should compute attraction for connected nodes', () => {
      const nodes = new Map<string, PositionedNode>([
        [
          'a',
          {
            id: 'a',
            position: { x: 0, y: 0 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
        [
          'b',
          {
            id: 'b',
            position: { x: 500, y: 0 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
      ])

      const edges = [{ id: 'e1', sourceId: 'a', targetId: 'b', waypoints: [] }]

      const forces = computeForces(nodes, edges, {
        attractionStrength: 0.1,
        targetEdgeLength: 150,
      })

      // Node a should be pulled right (toward b)
      expect(forces.get('a')!.x).toBeGreaterThan(0)
      // Node b should be pulled left (toward a)
      expect(forces.get('b')!.x).toBeLessThan(0)
    })

    it('should not apply forces to locked nodes', () => {
      const nodes = new Map<string, PositionedNode>([
        [
          'a',
          {
            id: 'a',
            position: { x: 0, y: 0 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: true, // Locked!
            velocity: { x: 0, y: 0 },
          },
        ],
        [
          'b',
          {
            id: 'b',
            position: { x: 10, y: 0 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
      ])

      const forces = computeForces(nodes, [], { repulsionStrength: 1000 })

      // Locked node should have zero force
      expect(forces.get('a')!.x).toBe(0)
      expect(forces.get('a')!.y).toBe(0)
    })
  })

  describe('routeEdges', () => {
    it('should create Manhattan routes', () => {
      const nodes = new Map<string, PositionedNode>([
        [
          'a',
          {
            id: 'a',
            position: { x: 0, y: 0 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
        [
          'b',
          {
            id: 'b',
            position: { x: 200, y: 100 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
      ])

      const edges = [{ id: 'e1', sourceId: 'a', targetId: 'b', waypoints: [] }]

      const routed = routeEdges(nodes, edges, { manhattanRouting: true })

      // Manhattan routing should have at least 3 waypoints (start, corner, end)
      // or 2 if aligned
      expect(routed[0].waypoints.length).toBeGreaterThanOrEqual(2)

      // Check that all segments are axis-aligned
      const waypoints = routed[0].waypoints
      for (let i = 1; i < waypoints.length; i++) {
        const prev = waypoints[i - 1]
        const curr = waypoints[i]
        // Either x or y should be equal (axis-aligned)
        expect(prev.x === curr.x || prev.y === curr.y).toBe(true)
      }
    })

    it('should handle direct routing', () => {
      const nodes = new Map<string, PositionedNode>([
        [
          'a',
          {
            id: 'a',
            position: { x: 0, y: 0 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
        [
          'b',
          {
            id: 'b',
            position: { x: 200, y: 100 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
      ])

      const edges = [{ id: 'e1', sourceId: 'a', targetId: 'b', waypoints: [] }]

      const routed = routeEdges(nodes, edges, { manhattanRouting: false })

      // Direct routing should have exactly 2 waypoints
      expect(routed[0].waypoints.length).toBe(2)
    })
  })

  describe('calculateBounds', () => {
    it('should calculate bounds with padding', () => {
      const nodes = new Map<string, PositionedNode>([
        [
          'a',
          {
            id: 'a',
            position: { x: 100, y: 100 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
        [
          'b',
          {
            id: 'b',
            position: { x: 300, y: 200 },
            width: 50,
            height: 50,
            orientation: 0,
            locked: false,
            velocity: { x: 0, y: 0 },
          },
        ],
      ])

      const bounds = calculateBounds(nodes, 20)

      // Bounds should include padding
      expect(bounds.x).toBeLessThan(100 - 25) // 100 - half width
      expect(bounds.y).toBeLessThan(100 - 25)
      expect(bounds.x + bounds.width).toBeGreaterThan(300 + 25)
      expect(bounds.y + bounds.height).toBeGreaterThan(200 + 25)
    })

    it('should handle empty nodes', () => {
      const nodes = new Map<string, PositionedNode>()
      const bounds = calculateBounds(nodes, 20)

      expect(bounds.width).toBe(0)
      expect(bounds.height).toBe(0)
    })
  })
})
