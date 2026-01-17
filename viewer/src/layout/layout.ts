import type { CircuitGraph, CircuitGraphNode } from '@/graph'
import type {
  Position,
  Vector,
  BoundingBox,
  PositionedNode,
  RoutedEdge,
  Waypoint,
  LayoutResult,
  LayoutOptions,
  SimulationState,
} from './types'

/**
 * Default layout options
 */
const DEFAULT_OPTIONS: Required<LayoutOptions> = {
  maxIterations: 300,
  initialTemperature: 100,
  coolingFactor: 0.95,
  convergenceThreshold: 0.1,
  repulsionStrength: 1000,
  attractionStrength: 0.1,
  targetEdgeLength: 150,
  padding: 50,
  manhattanRouting: true,
  centerNode: '',
}

/**
 * Get node dimensions from graph node type
 */
function getNodeDimensions(node: CircuitGraphNode): { width: number; height: number } {
  switch (node.type) {
    case 'component':
    case 'inline_passive':
      return { width: 60, height: 40 }
    case 'subcircuit':
      return { width: 100, height: 80 }
    case 'net':
      return { width: 30, height: 30 }
    default:
      return { width: 40, height: 40 }
  }
}

/**
 * Initialize positioned nodes from graph
 */
function initializeNodes(graph: CircuitGraph): Map<string, PositionedNode> {
  const nodes = new Map<string, PositionedNode>()

  // Place nodes in a grid initially
  const gridSize = Math.ceil(Math.sqrt(graph.nodes.size))
  const spacing = 200

  let i = 0
  for (const [id, graphNode] of graph.nodes) {
    const col = i % gridSize
    const row = Math.floor(i / gridSize)
    const dimensions = getNodeDimensions(graphNode)

    nodes.set(id, {
      id,
      position: {
        x: col * spacing + (Math.random() - 0.5) * 50,
        y: row * spacing + (Math.random() - 0.5) * 50,
      },
      width: dimensions.width,
      height: dimensions.height,
      orientation: 0,
      locked: false,
      velocity: { x: 0, y: 0 },
    })

    i++
  }

  return nodes
}

/**
 * Compute repulsion force between two nodes
 */
function computeRepulsion(a: PositionedNode, b: PositionedNode, strength: number): Vector {
  const dx = a.position.x - b.position.x
  const dy = a.position.y - b.position.y
  const distSq = dx * dx + dy * dy
  const minDist = (a.width + b.width) / 2 + 20 // Minimum distance with buffer

  // Avoid division by zero
  const dist = Math.max(Math.sqrt(distSq), 1)

  // Stronger repulsion when closer than minimum distance
  const effectiveDist = Math.max(dist, minDist)
  const force = strength / (effectiveDist * effectiveDist)

  return {
    x: (dx / dist) * force,
    y: (dy / dist) * force,
  }
}

/**
 * Compute attraction force between connected nodes
 */
function computeAttraction(
  a: PositionedNode,
  b: PositionedNode,
  strength: number,
  targetLength: number
): Vector {
  const dx = b.position.x - a.position.x
  const dy = b.position.y - a.position.y
  const dist = Math.sqrt(dx * dx + dy * dy)

  // No attraction if already at target length
  if (dist === 0) return { x: 0, y: 0 }

  // Spring-like force: stronger when far from target length
  const displacement = dist - targetLength
  const force = strength * displacement

  return {
    x: (dx / dist) * force,
    y: (dy / dist) * force,
  }
}

/**
 * Compute all forces on nodes
 */
export function computeForces(
  nodes: Map<string, PositionedNode>,
  edges: Array<{ id: string; sourceId: string; targetId: string }>,
  options: Partial<LayoutOptions>
): Map<string, Vector> {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  const forces = new Map<string, Vector>()

  // Initialize forces to zero
  for (const id of nodes.keys()) {
    forces.set(id, { x: 0, y: 0 })
  }

  const nodeArray = Array.from(nodes.values())

  // Compute repulsion between all node pairs
  for (let i = 0; i < nodeArray.length; i++) {
    for (let j = i + 1; j < nodeArray.length; j++) {
      const a = nodeArray[i]
      const b = nodeArray[j]

      const repulsion = computeRepulsion(a, b, opts.repulsionStrength)

      // Apply force to a (unless locked)
      if (!a.locked) {
        const fa = forces.get(a.id)!
        fa.x += repulsion.x
        fa.y += repulsion.y
      }

      // Apply opposite force to b (unless locked)
      if (!b.locked) {
        const fb = forces.get(b.id)!
        fb.x -= repulsion.x
        fb.y -= repulsion.y
      }
    }
  }

  // Compute attraction for connected nodes
  for (const edge of edges) {
    const a = nodes.get(edge.sourceId)
    const b = nodes.get(edge.targetId)

    if (!a || !b) continue

    const attraction = computeAttraction(a, b, opts.attractionStrength, opts.targetEdgeLength)

    // Apply force to a (unless locked)
    if (!a.locked) {
      const fa = forces.get(a.id)!
      fa.x += attraction.x
      fa.y += attraction.y
    }

    // Apply opposite force to b (unless locked)
    if (!b.locked) {
      const fb = forces.get(b.id)!
      fb.x -= attraction.x
      fb.y -= attraction.y
    }
  }

  return forces
}

/**
 * Apply forces to update node positions
 */
function applyForces(
  nodes: Map<string, PositionedNode>,
  forces: Map<string, Vector>,
  state: SimulationState,
  damping: number = 0.8
): number {
  let maxForce = 0

  for (const [id, node] of nodes) {
    if (node.locked) continue

    const force = forces.get(id)!
    const forceMagnitude = Math.sqrt(force.x * force.x + force.y * force.y)
    maxForce = Math.max(maxForce, forceMagnitude)

    // Apply force with temperature scaling
    const scale = Math.min(state.temperature, forceMagnitude) / Math.max(forceMagnitude, 0.01)

    // Update velocity with damping
    node.velocity.x = (node.velocity.x + force.x * scale) * damping
    node.velocity.y = (node.velocity.y + force.y * scale) * damping

    // Update position
    node.position.x += node.velocity.x
    node.position.y += node.velocity.y
  }

  return maxForce
}

/**
 * Route a single edge using Manhattan routing
 */
function routeManhattan(source: Position, target: Position): Waypoint[] {
  const waypoints: Waypoint[] = []

  waypoints.push({ x: source.x, y: source.y, isJunction: false })

  // Simple L-shape routing
  const midY = (source.y + target.y) / 2

  // Go vertical first, then horizontal
  if (Math.abs(source.x - target.x) > 1 && Math.abs(source.y - target.y) > 1) {
    waypoints.push({ x: source.x, y: midY, isJunction: false })
    waypoints.push({ x: target.x, y: midY, isJunction: false })
  }

  waypoints.push({ x: target.x, y: target.y, isJunction: false })

  return waypoints
}

/**
 * Route a single edge directly
 */
function routeDirect(source: Position, target: Position): Waypoint[] {
  return [
    { x: source.x, y: source.y, isJunction: false },
    { x: target.x, y: target.y, isJunction: false },
  ]
}

/**
 * Get connection point on a node for a given pin
 */
function getConnectionPoint(node: PositionedNode, pin?: string): Position {
  // For now, just use the center of the node
  // In a full implementation, we'd look up the pin position from the symbol
  const halfWidth = node.width / 2
  const halfHeight = node.height / 2

  // Default pin positions based on common conventions
  if (pin) {
    const pinLower = pin.toLowerCase()
    if (pinLower === '1' || pinLower === 'a' || pinLower === 'in') {
      return { x: node.position.x - halfWidth, y: node.position.y }
    }
    if (pinLower === '2' || pinLower === 'k' || pinLower === 'out') {
      return { x: node.position.x + halfWidth, y: node.position.y }
    }
    if (pinLower === 'gnd' || pinLower === 's' || pinLower === 'e') {
      return { x: node.position.x, y: node.position.y + halfHeight }
    }
    if (pinLower === 'vcc' || pinLower === 'd' || pinLower === 'c') {
      return { x: node.position.x, y: node.position.y - halfHeight }
    }
    if (pinLower === 'g' || pinLower === 'b') {
      return { x: node.position.x - halfWidth, y: node.position.y }
    }
  }

  return { x: node.position.x, y: node.position.y }
}

/**
 * Route all edges
 */
export function routeEdges(
  nodes: Map<string, PositionedNode>,
  edges: Array<{
    id: string
    sourceId: string
    targetId: string
    sourcePin?: string
    targetPin?: string
  }>,
  options: Partial<LayoutOptions>
): RoutedEdge[] {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  const routed: RoutedEdge[] = []

  for (const edge of edges) {
    const sourceNode = nodes.get(edge.sourceId)
    const targetNode = nodes.get(edge.targetId)

    if (!sourceNode || !targetNode) {
      continue
    }

    const sourcePos = getConnectionPoint(sourceNode, edge.sourcePin)
    const targetPos = getConnectionPoint(targetNode, edge.targetPin)

    const waypoints = opts.manhattanRouting
      ? routeManhattan(sourcePos, targetPos)
      : routeDirect(sourcePos, targetPos)

    routed.push({
      id: edge.id,
      sourceId: edge.sourceId,
      sourcePin: edge.sourcePin,
      targetId: edge.targetId,
      targetPin: edge.targetPin,
      waypoints,
    })
  }

  return routed
}

/**
 * Calculate bounding box for all nodes
 */
export function calculateBounds(nodes: Map<string, PositionedNode>, padding: number): BoundingBox {
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

/**
 * Layout a circuit graph
 */
export function layoutGraph(graph: CircuitGraph, options: LayoutOptions = {}): LayoutResult {
  const opts = { ...DEFAULT_OPTIONS, ...options }

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

  // Initialize nodes
  const nodes = initializeNodes(graph)

  // Convert graph edges to simple format
  const simpleEdges = graph.edges.map((e) => ({
    id: e.id,
    sourceId: e.sourceId,
    targetId: e.targetId,
    sourcePin: e.sourcePin,
    targetPin: e.targetPin,
  }))

  // Simulation state
  const state: SimulationState = {
    temperature: opts.initialTemperature,
    iteration: 0,
    maxForce: Infinity,
  }

  // Run force-directed simulation
  while (state.iteration < opts.maxIterations && state.maxForce > opts.convergenceThreshold) {
    // Compute forces
    const forces = computeForces(nodes, simpleEdges, opts)

    // Apply forces
    state.maxForce = applyForces(nodes, forces, state)

    // Cool down
    state.temperature *= opts.coolingFactor
    state.iteration++
  }

  // Route edges
  const routedEdges = routeEdges(nodes, simpleEdges, opts)

  // Calculate bounds
  const bounds = calculateBounds(nodes, opts.padding)

  return {
    nodes,
    edges: routedEdges,
    bounds,
    iterations: state.iteration,
    converged: state.maxForce <= opts.convergenceThreshold,
  }
}
