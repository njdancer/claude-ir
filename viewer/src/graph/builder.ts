import type { CircuitAST, Endpoint } from '@/parser'
import type {
  CircuitGraph,
  ComponentGraphNode,
  SubcircuitGraphNode,
  NetGraphNode,
  InlinePassiveGraphNode,
  GraphEdge,
} from './types'

/**
 * Power net patterns
 */
const POWER_NET_PATTERNS = [
  /^V(CC|DD|SS|EE|IN|OUT|BUS|BAT)$/i,
  /^GND$/i,
  /^GROUND$/i,
  /^\d+V\d*$/i, // e.g., 3V3, 5V, 12V
  /^[+-]?\d+(\.\d+)?V$/i, // e.g., +5V, -12V, 3.3V
]

/**
 * Check if a net name represents a power net
 */
function isPowerNet(name: string): boolean {
  return POWER_NET_PATTERNS.some((pattern) => pattern.test(name))
}

/**
 * Generate a unique node ID
 */
function nodeId(type: 'net' | 'comp' | 'sub' | 'passive', name: string): string {
  return `${type}:${name}`
}

/**
 * Generate a unique edge ID
 */
function edgeId(sourceId: string, targetId: string, index: number): string {
  return `edge:${sourceId}-${targetId}-${index}`
}

/**
 * Resolve an endpoint to a node ID
 * Returns the node ID and optional pin
 */
function resolveEndpoint(
  endpoint: Endpoint,
  graph: CircuitGraph
): { nodeId: string; pin?: string } | null {
  // Check if it's a component/subcircuit pin reference
  if (endpoint.pin) {
    // Check components
    const compId = nodeId('comp', endpoint.ref)
    if (graph.nodes.has(compId)) {
      return { nodeId: compId, pin: endpoint.pin }
    }

    // Check subcircuits
    const subId = nodeId('sub', endpoint.ref)
    if (graph.nodes.has(subId)) {
      return { nodeId: subId, pin: endpoint.pin }
    }

    // Check inline passives
    const passiveId = nodeId('passive', endpoint.ref)
    if (graph.nodes.has(passiveId)) {
      return { nodeId: passiveId, pin: endpoint.pin }
    }
  }

  // Check if it's a net reference
  const netId = nodeId('net', endpoint.ref)
  if (graph.nodes.has(netId)) {
    return { nodeId: netId }
  }

  // Check if it's a component without explicit pin
  const compId = nodeId('comp', endpoint.ref)
  if (graph.nodes.has(compId)) {
    return { nodeId: compId }
  }

  // Check if it's a subcircuit without explicit pin
  const subId = nodeId('sub', endpoint.ref)
  if (graph.nodes.has(subId)) {
    return { nodeId: subId }
  }

  // Check if it's an inline passive
  const passiveId = nodeId('passive', endpoint.ref)
  if (graph.nodes.has(passiveId)) {
    return { nodeId: passiveId }
  }

  // Not found - create implicit net
  const implicitNetId = nodeId('net', endpoint.ref)
  const implicitNet: NetGraphNode = {
    id: implicitNetId,
    type: 'net',
    label: endpoint.ref,
    name: endpoint.ref,
    isPower: isPowerNet(endpoint.ref),
    metadata: { implicit: true },
  }
  graph.nodes.set(implicitNetId, implicitNet)
  return { nodeId: implicitNetId }
}

/**
 * Track a pin on a component
 */
function trackPin(graph: CircuitGraph, nodeId: string, pin?: string): void {
  if (!pin) return

  const node = graph.nodes.get(nodeId)
  if (node?.type === 'component') {
    if (!node.pins.includes(pin)) {
      node.pins.push(pin)
    }
  }
}

/**
 * Build a circuit graph from an AST
 */
export function buildGraph(ast: CircuitAST): CircuitGraph {
  const graph: CircuitGraph = {
    nodes: new Map(),
    edges: [],
    filename: ast.filename,
    metadata: { ...ast.frontmatter },
  }

  // Create net nodes
  for (const [name, netNode] of ast.nets) {
    const net: NetGraphNode = {
      id: nodeId('net', name),
      type: 'net',
      label: name,
      name,
      isPower: isPowerNet(name),
      metadata: {
        location: netNode.location,
      },
    }
    graph.nodes.set(net.id, net)
  }

  // Create component nodes
  for (const [ref, compNode] of ast.components) {
    const comp: ComponentGraphNode = {
      id: nodeId('comp', ref),
      type: 'component',
      label: `${ref}: ${compNode.componentType}`,
      ref,
      componentType: compNode.componentType,
      params: compNode.params,
      pins: [],
      metadata: {
        location: compNode.location,
      },
    }
    graph.nodes.set(comp.id, comp)
  }

  // Create subcircuit nodes
  for (const [ref, subNode] of ast.subcircuits) {
    const sub: SubcircuitGraphNode = {
      id: nodeId('sub', ref),
      type: 'subcircuit',
      label: ref,
      ref,
      path: subNode.path,
      exposedPins: [],
      expanded: false,
      metadata: {
        location: subNode.location,
      },
    }

    // If resolved, extract exposed pins from nets
    if (subNode.resolved) {
      for (const [netName] of subNode.resolved.nets) {
        sub.exposedPins.push(netName)
      }
    }

    graph.nodes.set(sub.id, sub)
  }

  // Create inline passive nodes
  for (const passive of ast.inlinePassives) {
    const passiveNode: InlinePassiveGraphNode = {
      id: nodeId('passive', passive.ref),
      type: 'inline_passive',
      label: `${passive.ref}: ${passive.value}`,
      ref: passive.ref,
      passiveType: passive.passiveType,
      value: passive.value,
      metadata: {
        location: passive.location,
      },
    }
    graph.nodes.set(passiveNode.id, passiveNode)
  }

  let edgeIndex = 0

  // Create edges for direct connections
  for (const conn of ast.connections) {
    const source = resolveEndpoint(conn.from, graph)
    const target = resolveEndpoint(conn.to, graph)

    if (source && target) {
      const edge: GraphEdge = {
        id: edgeId(source.nodeId, target.nodeId, edgeIndex++),
        sourceId: source.nodeId,
        sourcePin: source.pin,
        targetId: target.nodeId,
        targetPin: target.pin,
      }
      graph.edges.push(edge)

      // Track pins
      trackPin(graph, source.nodeId, source.pin)
      trackPin(graph, target.nodeId, target.pin)
    }
  }

  // Create edges for inline passives
  for (const passive of ast.inlinePassives) {
    const passiveNodeId = nodeId('passive', passive.ref)
    const source = resolveEndpoint(passive.from, graph)
    const target = resolveEndpoint(passive.to, graph)

    if (source) {
      const edge: GraphEdge = {
        id: edgeId(source.nodeId, passiveNodeId, edgeIndex++),
        sourceId: source.nodeId,
        sourcePin: source.pin,
        targetId: passiveNodeId,
        targetPin: '1',
      }
      graph.edges.push(edge)
      trackPin(graph, source.nodeId, source.pin)
    }

    if (target) {
      const edge: GraphEdge = {
        id: edgeId(passiveNodeId, target.nodeId, edgeIndex++),
        sourceId: passiveNodeId,
        sourcePin: '2',
        targetId: target.nodeId,
        targetPin: target.pin,
      }
      graph.edges.push(edge)
      trackPin(graph, target.nodeId, target.pin)
    }
  }

  return graph
}

/**
 * Build a graph from a resolved AST (including sub-circuits)
 */
export function buildResolvedGraph(ast: CircuitAST): CircuitGraph {
  const graph = buildGraph(ast)

  // Build child graphs for resolved subcircuits
  for (const [, subNode] of ast.subcircuits) {
    if (subNode.resolved) {
      const subId = nodeId('sub', subNode.ref)
      const subGraphNode = graph.nodes.get(subId)
      if (subGraphNode?.type === 'subcircuit') {
        subGraphNode.childGraph = buildResolvedGraph(subNode.resolved)
      }
    }
  }

  return graph
}
