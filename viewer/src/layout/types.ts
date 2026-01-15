import type { SymbolOrientation } from '@/symbols'

/**
 * 2D position
 */
export interface Position {
  x: number
  y: number
}

/**
 * 2D vector for forces and velocities
 */
export interface Vector {
  x: number
  y: number
}

/**
 * Bounding box
 */
export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

/**
 * A positioned node in the layout
 */
export interface PositionedNode {
  /** Node ID from the graph */
  id: string
  /** Position (center of node) */
  position: Position
  /** Width of the node (from symbol) */
  width: number
  /** Height of the node (from symbol) */
  height: number
  /** Symbol orientation */
  orientation: SymbolOrientation
  /** Whether node is locked (won't move during layout) */
  locked: boolean
  /** Velocity for force-directed layout */
  velocity: Vector
}

/**
 * A waypoint on a wire route
 */
export interface Waypoint {
  x: number
  y: number
  /** Whether this is a junction point (wire crossing with connection) */
  isJunction: boolean
}

/**
 * A routed edge (wire) between nodes
 */
export interface RoutedEdge {
  /** Edge ID from the graph */
  id: string
  /** Source node ID */
  sourceId: string
  /** Source pin name */
  sourcePin?: string
  /** Target node ID */
  targetId: string
  /** Target pin name */
  targetPin?: string
  /** Waypoints along the route */
  waypoints: Waypoint[]
}

/**
 * Complete layout result
 */
export interface LayoutResult {
  /** All positioned nodes */
  nodes: Map<string, PositionedNode>
  /** All routed edges */
  edges: RoutedEdge[]
  /** Layout bounding box */
  bounds: BoundingBox
  /** Number of iterations performed */
  iterations: number
  /** Whether layout converged (stable) */
  converged: boolean
}

/**
 * Options for the layout algorithm
 */
export interface LayoutOptions {
  /** Maximum iterations before stopping (default: 300) */
  maxIterations?: number
  /** Initial temperature for simulated annealing (default: 100) */
  initialTemperature?: number
  /** Cooling factor per iteration (default: 0.95) */
  coolingFactor?: number
  /** Convergence threshold - stop when max force below this (default: 0.1) */
  convergenceThreshold?: number
  /** Repulsion strength between nodes (default: 1000) */
  repulsionStrength?: number
  /** Attraction strength for connected nodes (default: 0.1) */
  attractionStrength?: number
  /** Target edge length (default: 150) */
  targetEdgeLength?: number
  /** Padding around the layout (default: 50) */
  padding?: number
  /** Whether to use Manhattan routing (default: true) */
  manhattanRouting?: boolean
  /** Node to use as layout center (optional) */
  centerNode?: string
}

/**
 * Internal simulation state
 */
export interface SimulationState {
  /** Current temperature */
  temperature: number
  /** Current iteration */
  iteration: number
  /** Maximum force magnitude in last iteration */
  maxForce: number
}
