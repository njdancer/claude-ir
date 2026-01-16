# Graph API

The graph module converts a parsed AST into a queryable circuit graph model. The graph represents components as nodes and connections as edges, enabling traversal and filtering operations.

## Quick Start

```typescript
import { parse } from '@/parser'
import { buildGraph, filterByNets, getGraphStats } from '@/graph'

const source = `
[VCC]: net
[GND]: net
[R1]: resistor(10k)
[C1]: capacitor(100nF)
[VCC --- R1.1]
[R1.2 --- C1.1]
[C1.2 --- GND]
`

const parseResult = parse(source, 'circuit.md')
const graph = buildGraph(parseResult.ast)

console.log(getGraphStats(graph))
// { nodes: 5, edges: 4, components: 2, nets: 2 }
```

## Building Graphs

### `buildGraph(ast: CircuitAST): CircuitGraph`

Converts a parsed AST into a circuit graph.

**Parameters:**
- `ast` - A `CircuitAST` from the parser

**Returns:** `CircuitGraph`
- `nodes` - Map of node ID to `CircuitGraphNode`
- `edges` - Array of `GraphEdge` connections
- `filename` - Source filename
- `metadata` - Frontmatter metadata

### `buildResolvedGraph(ast: CircuitAST, loader: FileLoader): Promise<CircuitGraph>`

Builds a graph with resolved sub-circuits expanded inline.

## Node Types

### ComponentGraphNode

```typescript
interface ComponentGraphNode {
  type: 'component'
  id: string            // Unique identifier
  ref: string           // Reference designator (e.g., 'R1')
  componentType: string // Type (e.g., 'resistor')
  params: string[]      // Parameters (e.g., ['10k'])
  pins: string[]        // Known pins (e.g., ['1', '2'])
  label: string         // Display label
  metadata: Record<string, unknown>
}
```

### NetGraphNode

```typescript
interface NetGraphNode {
  type: 'net'
  id: string
  name: string     // Net name (e.g., 'VCC')
  isPower: boolean // True for power nets
  label: string
  metadata: Record<string, unknown>
}
```

### SubcircuitGraphNode

```typescript
interface SubcircuitGraphNode {
  type: 'subcircuit'
  id: string
  ref: string
  path: string
  exposedPins: string[]
  expanded: boolean
  childGraph?: CircuitGraph  // When expanded
  label: string
  metadata: Record<string, unknown>
}
```

### InlinePassiveGraphNode

```typescript
interface InlinePassiveGraphNode {
  type: 'inline_passive'
  id: string
  ref: string              // Generated ref (e.g., '_R1')
  passiveType: 'resistor' | 'capacitor' | 'inductor' | 'fuse'
  value: string            // Value (e.g., '10k')
  label: string
  metadata: Record<string, unknown>
}
```

## Edge Structure

```typescript
interface GraphEdge {
  id: string
  sourceId: string
  sourcePin?: string  // Pin on source component
  targetId: string
  targetPin?: string  // Pin on target component
}
```

## Query Functions

### `getAdjacentNodes(graph: CircuitGraph, nodeId: string): CircuitGraphNode[]`

Returns all nodes directly connected to the given node.

```typescript
const neighbors = getAdjacentNodes(graph, 'R1')
// Returns nodes connected to R1
```

### `getEdgesForNode(graph: CircuitGraph, nodeId: string): GraphEdge[]`

Returns all edges connected to a node.

### `getNodesByType(graph: CircuitGraph, type: NodeType): CircuitGraphNode[]`

Returns all nodes of a specific type.

```typescript
const components = getNodesByType(graph, 'component')
const nets = getNodesByType(graph, 'net')
```

### `getComponentsByType(graph: CircuitGraph, componentType: string): ComponentGraphNode[]`

Returns components matching a specific type.

```typescript
const resistors = getComponentsByType(graph, 'resistor')
```

### `getNodesOnNet(graph: CircuitGraph, netName: string): CircuitGraphNode[]`

Returns all nodes connected to a specific net.

```typescript
const vccNodes = getNodesOnNet(graph, 'VCC')
```

### `bfsTraversal(graph: CircuitGraph, startId: string, maxDepth?: number): string[]`

Performs breadth-first traversal from a starting node.

```typescript
// Get all nodes within 2 hops of R1
const nearby = bfsTraversal(graph, 'R1', 2)
```

## Filtering Functions

### `filterByNets(graph: CircuitGraph, netNames: string[]): QueryResult`

Extracts a subgraph containing only nodes connected to specified nets.

```typescript
const { graph: filtered, boundaryNodes } = filterByNets(graph, ['VCC', 'GND'])
```

### `filterByComponents(graph: CircuitGraph, refs: string[]): QueryResult`

Extracts a subgraph containing specified components and their connections.

```typescript
const { graph: filtered } = filterByComponents(graph, ['R1', 'R2', 'C1'])
```

### `filterByComponentTypes(graph: CircuitGraph, types: string[]): QueryResult`

Filters to components of specific types.

```typescript
const { graph: filtered } = filterByComponentTypes(graph, ['resistor', 'capacitor'])
```

### `filterByNeighborhood(graph: CircuitGraph, centerId: string, depth: number): QueryResult`

Extracts a subgraph containing a component and its neighbors within a certain depth.

```typescript
// Get R1 and everything within 2 connections
const { graph: filtered } = filterByNeighborhood(graph, 'R1', 2)
```

### `filterGraph(graph: CircuitGraph, criteria: FilterCriteria): QueryResult`

General-purpose filter accepting multiple criteria.

```typescript
const { graph: filtered } = filterGraph(graph, {
  nets: ['VCC'],
  componentTypes: ['resistor'],
  neighborhoodCenter: 'U1',
  neighborhoodDepth: 1,
})
```

## Statistics

### `getGraphStats(graph: CircuitGraph): GraphStats`

Returns statistics about the graph.

```typescript
const stats = getGraphStats(graph)
// {
//   nodeCount: 10,
//   edgeCount: 15,
//   componentCount: 6,
//   netCount: 3,
//   subcircuitCount: 1,
// }
```

## QueryResult

Filter functions return a `QueryResult` object:

```typescript
interface QueryResult {
  graph: CircuitGraph      // The filtered subgraph
  boundaryNodes: Set<string>  // Nodes at the filter boundary
}
```

Boundary nodes are useful for showing "fade out" effects at the edges of a filtered view.

## Example: Building a Component Inspector

```typescript
import { buildGraph, getAdjacentNodes, getEdgesForNode } from '@/graph'

function inspectComponent(graph: CircuitGraph, ref: string) {
  const node = graph.nodes.get(ref)
  if (!node || node.type !== 'component') return null

  const neighbors = getAdjacentNodes(graph, ref)
  const edges = getEdgesForNode(graph, ref)

  return {
    component: node,
    connections: edges.map(edge => ({
      pin: edge.sourceId === ref ? edge.sourcePin : edge.targetPin,
      connectedTo: edge.sourceId === ref ? edge.targetId : edge.sourceId,
    })),
    neighborCount: neighbors.length,
  }
}
```
