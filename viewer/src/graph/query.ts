import type {
  CircuitGraph,
  CircuitGraphNode,
  GraphEdge,
  FilterCriteria,
  QueryResult,
} from './types'

/**
 * Create an empty graph
 */
function createEmptyGraph(source: CircuitGraph): CircuitGraph {
  return {
    nodes: new Map(),
    edges: [],
    filename: source.filename,
    metadata: { ...source.metadata },
  }
}

/**
 * Get all nodes adjacent to a given node
 */
export function getAdjacentNodes(graph: CircuitGraph, nodeId: string): Set<string> {
  const adjacent = new Set<string>()

  for (const edge of graph.edges) {
    if (edge.sourceId === nodeId) {
      adjacent.add(edge.targetId)
    }
    if (edge.targetId === nodeId) {
      adjacent.add(edge.sourceId)
    }
  }

  return adjacent
}

/**
 * Get all edges connected to a node
 */
export function getEdgesForNode(graph: CircuitGraph, nodeId: string): GraphEdge[] {
  return graph.edges.filter((e) => e.sourceId === nodeId || e.targetId === nodeId)
}

/**
 * Get all nodes of a specific type
 */
export function getNodesByType(
  graph: CircuitGraph,
  type: CircuitGraphNode['type']
): CircuitGraphNode[] {
  return Array.from(graph.nodes.values()).filter((n) => n.type === type)
}

/**
 * Get all components of a specific component type
 */
export function getComponentsByType(graph: CircuitGraph, componentType: string): CircuitGraphNode[] {
  return Array.from(graph.nodes.values()).filter(
    (n) => n.type === 'component' && n.componentType === componentType
  )
}

/**
 * Get all nodes connected to a specific net
 */
export function getNodesOnNet(graph: CircuitGraph, netName: string): Set<string> {
  const netId = `net:${netName}`
  if (!graph.nodes.has(netId)) {
    return new Set()
  }

  const nodes = new Set<string>()
  nodes.add(netId)

  for (const edge of graph.edges) {
    if (edge.sourceId === netId) {
      nodes.add(edge.targetId)
    }
    if (edge.targetId === netId) {
      nodes.add(edge.sourceId)
    }
  }

  return nodes
}

/**
 * Breadth-first traversal from a starting node with depth limit
 */
export function bfsTraversal(
  graph: CircuitGraph,
  startId: string,
  maxDepth: number = Infinity
): Map<string, number> {
  const distances = new Map<string, number>()
  const queue: Array<{ id: string; depth: number }> = []

  if (!graph.nodes.has(startId)) {
    return distances
  }

  queue.push({ id: startId, depth: 0 })
  distances.set(startId, 0)

  while (queue.length > 0) {
    const current = queue.shift()!

    if (current.depth >= maxDepth) {
      continue
    }

    const adjacent = getAdjacentNodes(graph, current.id)
    for (const neighborId of adjacent) {
      if (!distances.has(neighborId)) {
        distances.set(neighborId, current.depth + 1)
        queue.push({ id: neighborId, depth: current.depth + 1 })
      }
    }
  }

  return distances
}

/**
 * Extract a subgraph containing only specified nodes
 */
export function extractSubgraph(graph: CircuitGraph, nodeIds: Set<string>): CircuitGraph {
  const subgraph = createEmptyGraph(graph)

  // Copy nodes
  for (const nodeId of nodeIds) {
    const node = graph.nodes.get(nodeId)
    if (node) {
      subgraph.nodes.set(nodeId, { ...node })
    }
  }

  // Copy edges where both endpoints are in the subgraph
  for (const edge of graph.edges) {
    if (nodeIds.has(edge.sourceId) && nodeIds.has(edge.targetId)) {
      subgraph.edges.push({ ...edge })
    }
  }

  return subgraph
}

/**
 * Filter graph by net names - returns nodes connected to any of the specified nets
 */
export function filterByNets(graph: CircuitGraph, netNames: string[]): QueryResult {
  const includedNodes = new Set<string>()
  const boundaryNodes = new Set<string>()

  for (const netName of netNames) {
    const nodesOnNet = getNodesOnNet(graph, netName)
    nodesOnNet.forEach((id) => includedNodes.add(id))
  }

  // Find boundary nodes (connected to included nodes but not included)
  for (const nodeId of includedNodes) {
    const adjacent = getAdjacentNodes(graph, nodeId)
    for (const adjId of adjacent) {
      if (!includedNodes.has(adjId)) {
        boundaryNodes.add(adjId)
      }
    }
  }

  return {
    graph: extractSubgraph(graph, includedNodes),
    boundaryNodes,
  }
}

/**
 * Filter graph by component references
 */
export function filterByComponents(graph: CircuitGraph, componentRefs: string[]): QueryResult {
  const includedNodes = new Set<string>()
  const boundaryNodes = new Set<string>()

  for (const ref of componentRefs) {
    // Try different node ID prefixes
    for (const prefix of ['comp:', 'sub:', 'passive:']) {
      const nodeId = `${prefix}${ref}`
      if (graph.nodes.has(nodeId)) {
        includedNodes.add(nodeId)
        // Also include directly connected nets
        const adjacent = getAdjacentNodes(graph, nodeId)
        adjacent.forEach((id) => includedNodes.add(id))
      }
    }
  }

  // Find boundary nodes
  for (const nodeId of includedNodes) {
    const adjacent = getAdjacentNodes(graph, nodeId)
    for (const adjId of adjacent) {
      if (!includedNodes.has(adjId)) {
        boundaryNodes.add(adjId)
      }
    }
  }

  return {
    graph: extractSubgraph(graph, includedNodes),
    boundaryNodes,
  }
}

/**
 * Filter graph by component types
 */
export function filterByComponentTypes(graph: CircuitGraph, types: string[]): QueryResult {
  const includedNodes = new Set<string>()
  const boundaryNodes = new Set<string>()

  for (const [nodeId, node] of graph.nodes) {
    if (node.type === 'component' && types.includes(node.componentType)) {
      includedNodes.add(nodeId)
      // Also include directly connected nets
      const adjacent = getAdjacentNodes(graph, nodeId)
      adjacent.forEach((id) => includedNodes.add(id))
    }
    if (node.type === 'inline_passive' && types.includes(node.passiveType)) {
      includedNodes.add(nodeId)
      const adjacent = getAdjacentNodes(graph, nodeId)
      adjacent.forEach((id) => includedNodes.add(id))
    }
  }

  // Find boundary nodes
  for (const nodeId of includedNodes) {
    const adjacent = getAdjacentNodes(graph, nodeId)
    for (const adjId of adjacent) {
      if (!includedNodes.has(adjId)) {
        boundaryNodes.add(adjId)
      }
    }
  }

  return {
    graph: extractSubgraph(graph, includedNodes),
    boundaryNodes,
  }
}

/**
 * Filter graph to neighborhood around a component
 */
export function filterByNeighborhood(
  graph: CircuitGraph,
  centerRef: string,
  depth: number
): QueryResult {
  // Find the center node
  let centerId: string | null = null
  for (const prefix of ['comp:', 'sub:', 'passive:', 'net:']) {
    const nodeId = `${prefix}${centerRef}`
    if (graph.nodes.has(nodeId)) {
      centerId = nodeId
      break
    }
  }

  if (!centerId) {
    return {
      graph: createEmptyGraph(graph),
      boundaryNodes: new Set(),
    }
  }

  // BFS to find all nodes within depth
  const distances = bfsTraversal(graph, centerId, depth)
  const includedNodes = new Set(distances.keys())

  // Find boundary nodes (at depth+1)
  const boundaryNodes = new Set<string>()
  for (const nodeId of includedNodes) {
    if (distances.get(nodeId) === depth) {
      const adjacent = getAdjacentNodes(graph, nodeId)
      for (const adjId of adjacent) {
        if (!includedNodes.has(adjId)) {
          boundaryNodes.add(adjId)
        }
      }
    }
  }

  return {
    graph: extractSubgraph(graph, includedNodes),
    boundaryNodes,
  }
}

/**
 * Apply multiple filter criteria
 */
export function filterGraph(graph: CircuitGraph, criteria: FilterCriteria): QueryResult {
  let result: QueryResult = {
    graph,
    boundaryNodes: new Set(),
  }

  // Apply neighborhood filter first if specified (most restrictive)
  if (criteria.neighborhoodCenter && criteria.neighborhoodDepth !== undefined) {
    result = filterByNeighborhood(graph, criteria.neighborhoodCenter, criteria.neighborhoodDepth)
  }

  // Apply net filter
  if (criteria.nets && criteria.nets.length > 0) {
    const netResult = filterByNets(result.graph, criteria.nets)
    result = {
      graph: netResult.graph,
      boundaryNodes: new Set([...result.boundaryNodes, ...netResult.boundaryNodes]),
    }
  }

  // Apply component filter
  if (criteria.components && criteria.components.length > 0) {
    const compResult = filterByComponents(result.graph, criteria.components)
    result = {
      graph: compResult.graph,
      boundaryNodes: new Set([...result.boundaryNodes, ...compResult.boundaryNodes]),
    }
  }

  // Apply component type filter
  if (criteria.componentTypes && criteria.componentTypes.length > 0) {
    const typeResult = filterByComponentTypes(result.graph, criteria.componentTypes)
    result = {
      graph: typeResult.graph,
      boundaryNodes: new Set([...result.boundaryNodes, ...typeResult.boundaryNodes]),
    }
  }

  return result
}

/**
 * Get statistics about a graph
 */
export function getGraphStats(graph: CircuitGraph): {
  nodeCount: number
  edgeCount: number
  netCount: number
  componentCount: number
  subcircuitCount: number
  inlinePassiveCount: number
} {
  let netCount = 0
  let componentCount = 0
  let subcircuitCount = 0
  let inlinePassiveCount = 0

  for (const node of graph.nodes.values()) {
    switch (node.type) {
      case 'net':
        netCount++
        break
      case 'component':
        componentCount++
        break
      case 'subcircuit':
        subcircuitCount++
        break
      case 'inline_passive':
        inlinePassiveCount++
        break
    }
  }

  return {
    nodeCount: graph.nodes.size,
    edgeCount: graph.edges.length,
    netCount,
    componentCount,
    subcircuitCount,
    inlinePassiveCount,
  }
}
