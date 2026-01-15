/**
 * Graph node types
 */
export type NodeType = 'component' | 'subcircuit' | 'net' | 'inline_passive'

/**
 * Base interface for graph nodes
 */
export interface GraphNode {
  /** Unique identifier for the node */
  id: string
  /** Node type */
  type: NodeType
  /** Display label */
  label: string
  /** Additional metadata */
  metadata: Record<string, unknown>
}

/**
 * Component node in the graph
 */
export interface ComponentGraphNode extends GraphNode {
  type: 'component'
  /** Component reference designator */
  ref: string
  /** Component type (e.g., 'resistor', 'esp32') */
  componentType: string
  /** Component parameters */
  params: string[]
  /** Known pins on this component */
  pins: string[]
}

/**
 * Sub-circuit node (can be expanded)
 */
export interface SubcircuitGraphNode extends GraphNode {
  type: 'subcircuit'
  /** Reference designator */
  ref: string
  /** Path to sub-circuit file */
  path: string
  /** Exposed pins (from sub-circuit nets) */
  exposedPins: string[]
  /** Whether currently expanded */
  expanded: boolean
  /** Child graph (when expanded) */
  childGraph?: CircuitGraph
}

/**
 * Net node (electrical connection point)
 */
export interface NetGraphNode extends GraphNode {
  type: 'net'
  /** Net name */
  name: string
  /** Whether this is a power net (VCC, GND, etc.) */
  isPower: boolean
}

/**
 * Inline passive node (auto-generated component)
 */
export interface InlinePassiveGraphNode extends GraphNode {
  type: 'inline_passive'
  /** Generated reference (_R1, _C1, etc.) */
  ref: string
  /** Passive type */
  passiveType: 'resistor' | 'capacitor' | 'inductor' | 'fuse'
  /** Value (e.g., '10kΩ', '100nF') */
  value: string
}

/**
 * Union of all graph node types
 */
export type CircuitGraphNode =
  | ComponentGraphNode
  | SubcircuitGraphNode
  | NetGraphNode
  | InlinePassiveGraphNode

/**
 * Edge in the circuit graph (connection)
 */
export interface GraphEdge {
  /** Unique edge identifier */
  id: string
  /** Source node ID */
  sourceId: string
  /** Source pin (if applicable) */
  sourcePin?: string
  /** Target node ID */
  targetId: string
  /** Target pin (if applicable) */
  targetPin?: string
}

/**
 * Circuit graph representation
 */
export interface CircuitGraph {
  /** All nodes in the graph */
  nodes: Map<string, CircuitGraphNode>
  /** All edges in the graph */
  edges: GraphEdge[]
  /** Source filename */
  filename: string
  /** Frontmatter metadata */
  metadata: {
    name?: string
    description?: string
    [key: string]: unknown
  }
}

/**
 * Filter criteria for extracting subgraphs
 */
export interface FilterCriteria {
  /** Filter by net names */
  nets?: string[]
  /** Filter by component references */
  components?: string[]
  /** Filter by component types */
  componentTypes?: string[]
  /** Starting component for neighborhood filter */
  neighborhoodCenter?: string
  /** Depth limit for neighborhood filter */
  neighborhoodDepth?: number
}

/**
 * Result of a graph query
 */
export interface QueryResult {
  /** Filtered subgraph */
  graph: CircuitGraph
  /** Nodes that were filtered out but connect to included nodes */
  boundaryNodes: Set<string>
}
