import ELK from 'elkjs/lib/elk.bundled.js'
import type { CircuitGraph, CircuitGraphNode } from '@/graph'
import type { PositionedNode, RoutedEdge, Waypoint, LayoutResult, BoundingBox } from './types'

// ELK types (simplified to avoid import issues)
interface ElkPort {
  id: string
  width?: number
  height?: number
  x?: number
  y?: number
  layoutOptions?: Record<string, string>
}

interface ElkLabel {
  text: string
  width?: number
  height?: number
}

interface ElkNode {
  id: string
  width?: number
  height?: number
  x?: number
  y?: number
  ports?: ElkPort[]
  labels?: ElkLabel[]
  children?: ElkNode[]
  edges?: ElkEdge[]
  layoutOptions?: Record<string, string>
}

interface ElkEdge {
  id: string
  sources: string[]
  targets: string[]
  sections?: ElkEdgeSection[]
}

interface ElkEdgeSection {
  startPoint: { x: number; y: number }
  endPoint: { x: number; y: number }
  bendPoints?: Array<{ x: number; y: number }>
}

/**
 * ELK layout options
 */
export interface ElkLayoutOptions {
  /** Layout direction: RIGHT (default), DOWN, LEFT, UP */
  direction?: 'RIGHT' | 'DOWN' | 'LEFT' | 'UP'
  /** Spacing between nodes in same layer */
  nodeNodeSpacing?: number
  /** Spacing between layers */
  layerSpacing?: number
  /** Edge routing style */
  edgeRouting?: 'ORTHOGONAL' | 'POLYLINE' | 'SPLINES'
  /** Whether to include port labels */
  showPortLabels?: boolean
  /** Padding around the layout */
  padding?: number
}

const DEFAULT_ELK_OPTIONS: Required<ElkLayoutOptions> = {
  direction: 'RIGHT',
  nodeNodeSpacing: 50,
  layerSpacing: 100,
  edgeRouting: 'ORTHOGONAL',
  showPortLabels: false,
  padding: 50,
}

/**
 * Get node dimensions based on type
 */
function getNodeDimensions(node: CircuitGraphNode): { width: number; height: number } {
  switch (node.type) {
    case 'component': {
      // Larger nodes for components with many pins
      const pinCount = node.pins?.length || 2
      const height = Math.max(60, pinCount * 15)
      return { width: 80, height }
    }
    case 'subcircuit':
      return { width: 120, height: 100 }
    case 'net':
      return { width: 20, height: 20 }
    case 'inline_passive':
      return { width: 60, height: 40 }
    default:
      return { width: 60, height: 40 }
  }
}

/**
 * Create ELK ports for a component node
 */
function createPorts(
  node: CircuitGraphNode,
  edges: Array<{ sourceId: string; targetId: string; sourcePin?: string; targetPin?: string }>
): ElkPort[] {
  const ports: ElkPort[] = []
  const seenPorts = new Set<string>()

  // Collect all pins used in connections for this node
  for (const edge of edges) {
    if (edge.sourceId === node.id && edge.sourcePin) {
      if (!seenPorts.has(edge.sourcePin)) {
        seenPorts.add(edge.sourcePin)
        ports.push({
          id: `${node.id}.${edge.sourcePin}`,
          layoutOptions: {
            'port.side': 'EAST',
          },
          width: 5,
          height: 5,
        })
      }
    }
    if (edge.targetId === node.id && edge.targetPin) {
      if (!seenPorts.has(edge.targetPin)) {
        seenPorts.add(edge.targetPin)
        ports.push({
          id: `${node.id}.${edge.targetPin}`,
          layoutOptions: {
            'port.side': 'WEST',
          },
          width: 5,
          height: 5,
        })
      }
    }
  }

  // For components, add pins from the node definition
  if (node.type === 'component' && node.pins) {
    for (let i = 0; i < node.pins.length; i++) {
      const pin = node.pins[i]
      if (!seenPorts.has(pin)) {
        seenPorts.add(pin)
        // Alternate sides for pins
        const side = i % 2 === 0 ? 'WEST' : 'EAST'
        ports.push({
          id: `${node.id}.${pin}`,
          layoutOptions: {
            'port.side': side,
          },
          width: 5,
          height: 5,
        })
      }
    }
  }

  // For subcircuits, add exposed pins
  if (node.type === 'subcircuit' && node.exposedPins) {
    for (let i = 0; i < node.exposedPins.length; i++) {
      const pin = node.exposedPins[i]
      if (!seenPorts.has(pin)) {
        seenPorts.add(pin)
        const side = i % 2 === 0 ? 'WEST' : 'EAST'
        ports.push({
          id: `${node.id}.${pin}`,
          layoutOptions: {
            'port.side': side,
          },
          width: 5,
          height: 5,
        })
      }
    }
  }

  // For inline passives, ensure we have at least two ports
  if (node.type === 'inline_passive' && ports.length < 2) {
    if (!seenPorts.has('1')) {
      ports.push({
        id: `${node.id}.1`,
        layoutOptions: { 'port.side': 'WEST' },
        width: 5,
        height: 5,
      })
    }
    if (!seenPorts.has('2')) {
      ports.push({
        id: `${node.id}.2`,
        layoutOptions: { 'port.side': 'EAST' },
        width: 5,
        height: 5,
      })
    }
  }

  return ports
}

/**
 * Convert CircuitGraph to ELK JSON format
 */
function graphToElk(graph: CircuitGraph, options: ElkLayoutOptions): ElkNode {
  const opts = { ...DEFAULT_ELK_OPTIONS, ...options }

  // Create ELK children (nodes)
  const children: ElkNode[] = []
  const simpleEdges = graph.edges.map((e) => ({
    sourceId: e.sourceId,
    targetId: e.targetId,
    sourcePin: e.sourcePin,
    targetPin: e.targetPin,
  }))

  for (const [id, node] of graph.nodes) {
    const dims = getNodeDimensions(node)
    const ports = createPorts(node, simpleEdges)

    const elkNode: ElkNode = {
      id,
      width: dims.width,
      height: dims.height,
      ports,
      labels: [
        {
          text: node.label,
          width: node.label.length * 7,
          height: 14,
        },
      ],
    }

    children.push(elkNode)
  }

  // Create ELK edges
  const edges: ElkEdge[] = graph.edges.map((edge, index) => {
    const sourcePort = edge.sourcePin ? `${edge.sourceId}.${edge.sourcePin}` : edge.sourceId
    const targetPort = edge.targetPin ? `${edge.targetId}.${edge.targetPin}` : edge.targetId

    return {
      id: edge.id || `e${index}`,
      sources: [sourcePort],
      targets: [targetPort],
    }
  })

  // Create root ELK graph
  const elkGraph: ElkNode = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': opts.direction,
      'elk.spacing.nodeNode': String(opts.nodeNodeSpacing),
      'elk.layered.spacing.nodeNodeBetweenLayers': String(opts.layerSpacing),
      'elk.edgeRouting': opts.edgeRouting,
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.considerModelOrder.strategy': 'PREFER_EDGES',
      'elk.portConstraints': 'FIXED_SIDE',
      'elk.layered.mergeEdges': 'true',
    },
    children,
    edges,
  }

  return elkGraph
}

/**
 * Convert ELK layout result back to our format
 */
function elkToLayoutResult(
  elkGraph: ElkNode,
  originalGraph: CircuitGraph,
  options: ElkLayoutOptions
): LayoutResult {
  const opts = { ...DEFAULT_ELK_OPTIONS, ...options }
  const nodes = new Map<string, PositionedNode>()
  const edges: RoutedEdge[] = []

  // Process nodes
  if (elkGraph.children) {
    for (const elkNode of elkGraph.children) {
      const originalNode = originalGraph.nodes.get(elkNode.id)
      if (!originalNode) continue

      nodes.set(elkNode.id, {
        id: elkNode.id,
        position: {
          x: (elkNode.x || 0) + (elkNode.width || 0) / 2,
          y: (elkNode.y || 0) + (elkNode.height || 0) / 2,
        },
        width: elkNode.width || 60,
        height: elkNode.height || 40,
        orientation: 0,
        locked: false,
        velocity: { x: 0, y: 0 },
      })
    }
  }

  // Process edges
  if (elkGraph.edges) {
    for (const elkEdge of elkGraph.edges) {
      const originalEdge = originalGraph.edges.find((e) => e.id === elkEdge.id)

      // Build waypoints from ELK sections
      const waypoints: Waypoint[] = []

      if (elkEdge.sections && elkEdge.sections.length > 0) {
        for (const section of elkEdge.sections) {
          // Add start point
          if (section.startPoint) {
            waypoints.push({
              x: section.startPoint.x,
              y: section.startPoint.y,
              isJunction: false,
            })
          }

          // Add bend points
          if (section.bendPoints) {
            for (const bend of section.bendPoints) {
              waypoints.push({
                x: bend.x,
                y: bend.y,
                isJunction: false,
              })
            }
          }

          // Add end point
          if (section.endPoint) {
            waypoints.push({
              x: section.endPoint.x,
              y: section.endPoint.y,
              isJunction: false,
            })
          }
        }
      }

      edges.push({
        id: elkEdge.id,
        sourceId: originalEdge?.sourceId || '',
        sourcePin: originalEdge?.sourcePin,
        targetId: originalEdge?.targetId || '',
        targetPin: originalEdge?.targetPin,
        waypoints,
      })
    }
  }

  // Calculate bounds
  const bounds = calculateBounds(nodes, opts.padding)

  return {
    nodes,
    edges,
    bounds,
    iterations: 1,
    converged: true,
  }
}

/**
 * Calculate bounding box for all nodes
 */
function calculateBounds(nodes: Map<string, PositionedNode>, padding: number): BoundingBox {
  if (nodes.size === 0) {
    return { x: 0, y: 0, width: 0, height: 0 }
  }

  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity

  for (const node of nodes.values()) {
    const halfWidth = node.width / 2
    const halfHeight = node.height / 2

    minX = Math.min(minX, node.position.x - halfWidth)
    minY = Math.min(minY, node.position.y - halfHeight)
    maxX = Math.max(maxX, node.position.x + halfWidth)
    maxY = Math.max(maxY, node.position.y + halfHeight)
  }

  return {
    x: minX - padding,
    y: minY - padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  }
}

// Singleton ELK instance
let elkInstance: InstanceType<typeof ELK> | null = null

function getElk(): InstanceType<typeof ELK> {
  if (!elkInstance) {
    elkInstance = new ELK()
  }
  return elkInstance
}

/**
 * Layout a circuit graph using ELK
 */
export async function layoutGraphElk(
  graph: CircuitGraph,
  options: ElkLayoutOptions = {}
): Promise<LayoutResult> {
  // Handle empty graph
  if (graph.nodes.size === 0) {
    return {
      nodes: new Map(),
      edges: [],
      bounds: { x: 0, y: 0, width: 0, height: 0 },
      iterations: 0,
      converged: true,
    }
  }

  const elk = getElk()
  const elkGraph = graphToElk(graph, options)

  try {
    // Cast to any to avoid type conflicts between our simplified types and ELK's types
    const layoutedGraph = await elk.layout(elkGraph as unknown as Parameters<typeof elk.layout>[0])
    return elkToLayoutResult(layoutedGraph as unknown as ElkNode, graph, options)
  } catch (error) {
    console.error('ELK layout failed:', error)
    // Return a basic fallback layout
    return fallbackLayout(graph, options)
  }
}

/**
 * Simple fallback layout when ELK fails
 */
function fallbackLayout(graph: CircuitGraph, options: ElkLayoutOptions): LayoutResult {
  const opts = { ...DEFAULT_ELK_OPTIONS, ...options }
  const nodes = new Map<string, PositionedNode>()

  const gridSize = Math.ceil(Math.sqrt(graph.nodes.size))
  const spacing = 150

  let i = 0
  for (const [id, node] of graph.nodes) {
    const col = i % gridSize
    const row = Math.floor(i / gridSize)
    const dims = getNodeDimensions(node)

    nodes.set(id, {
      id,
      position: {
        x: col * spacing + spacing / 2,
        y: row * spacing + spacing / 2,
      },
      width: dims.width,
      height: dims.height,
      orientation: 0,
      locked: false,
      velocity: { x: 0, y: 0 },
    })
    i++
  }

  // Simple direct edges
  const edges: RoutedEdge[] = graph.edges.map((edge) => {
    const sourceNode = nodes.get(edge.sourceId)
    const targetNode = nodes.get(edge.targetId)

    return {
      id: edge.id,
      sourceId: edge.sourceId,
      sourcePin: edge.sourcePin,
      targetId: edge.targetId,
      targetPin: edge.targetPin,
      waypoints: [
        { x: sourceNode?.position.x || 0, y: sourceNode?.position.y || 0, isJunction: false },
        { x: targetNode?.position.x || 0, y: targetNode?.position.y || 0, isJunction: false },
      ],
    }
  })

  return {
    nodes,
    edges,
    bounds: calculateBounds(nodes, opts.padding),
    iterations: 1,
    converged: true,
  }
}
