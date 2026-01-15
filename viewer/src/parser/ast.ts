import type { SourceLocation, ParseError } from './types'

/**
 * Base interface for all AST nodes
 */
export interface ASTNode {
  location: SourceLocation
}

/**
 * Frontmatter metadata from YAML header
 */
export interface Frontmatter {
  name?: string
  description?: string
  [key: string]: unknown
}

/**
 * Net declaration in the circuit
 */
export interface NetNode extends ASTNode {
  kind: 'net'
  name: string
}

/**
 * Component declaration in the circuit
 */
export interface ComponentNode extends ASTNode {
  kind: 'component'
  ref: string
  componentType: string
  params: string[]
}

/**
 * Sub-circuit reference
 */
export interface SubcircuitNode extends ASTNode {
  kind: 'subcircuit'
  ref: string
  path: string
  /** Resolved circuit AST (populated by resolver) */
  resolved?: CircuitAST
}

/**
 * Connection between two endpoints
 */
export interface ConnectionNode extends ASTNode {
  kind: 'connection'
  from: Endpoint
  to: Endpoint
}

/**
 * Inline passive component (auto-generated reference)
 */
export interface InlinePassiveNode extends ASTNode {
  kind: 'inline_passive'
  /** Auto-generated reference (e.g., _R1, _C1) */
  ref: string
  passiveType: 'resistor' | 'capacitor' | 'inductor' | 'fuse'
  value: string
  from: Endpoint
  to: Endpoint
}

/**
 * Property definition
 */
export interface PropertyNode extends ASTNode {
  kind: 'property'
  key: string
  value: string
}

/**
 * Endpoint reference (component pin or net)
 */
export interface Endpoint {
  /** Component reference (if pin) or net name */
  ref: string
  /** Pin name or number (if component pin) */
  pin?: string
  /** Raw string representation */
  raw: string
}

/**
 * Circuit AST root
 */
export interface CircuitAST {
  /** Source filename */
  filename: string
  /** YAML frontmatter metadata */
  frontmatter: Frontmatter
  /** All declared nets */
  nets: Map<string, NetNode>
  /** All declared components */
  components: Map<string, ComponentNode>
  /** All sub-circuit references */
  subcircuits: Map<string, SubcircuitNode>
  /** All connections */
  connections: ConnectionNode[]
  /** All inline passives (converted to connections + components) */
  inlinePassives: InlinePassiveNode[]
  /** All properties */
  properties: PropertyNode[]
  /** Parse errors encountered */
  errors: ParseError[]
}

/**
 * Parse an endpoint string into structured format
 *
 * Examples:
 *   "VCC" -> { ref: "VCC", raw: "VCC" }
 *   "U1.VCC" -> { ref: "U1", pin: "VCC", raw: "U1.VCC" }
 *   "R1#1" -> { ref: "R1", pin: "1", raw: "R1#1" }
 */
export function parseEndpoint(raw: string): Endpoint {
  const trimmed = raw.trim()

  // Check for numbered pin syntax: REF#PIN
  const hashMatch = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)#(\d+)$/)
  if (hashMatch) {
    return {
      ref: hashMatch[1],
      pin: hashMatch[2],
      raw: trimmed,
    }
  }

  // Check for named pin syntax: REF.PIN
  const dotMatch = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$/)
  if (dotMatch) {
    return {
      ref: dotMatch[1],
      pin: dotMatch[2],
      raw: trimmed,
    }
  }

  // Plain reference (net name or component without pin)
  return {
    ref: trimmed,
    raw: trimmed,
  }
}

/**
 * Create an empty Circuit AST
 */
export function createCircuitAST(filename: string): CircuitAST {
  return {
    filename,
    frontmatter: {},
    nets: new Map(),
    components: new Map(),
    subcircuits: new Map(),
    connections: [],
    inlinePassives: [],
    properties: [],
    errors: [],
  }
}
