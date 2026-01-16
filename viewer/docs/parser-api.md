# Parser API

The parser module converts circuit.md markdown files into an Abstract Syntax Tree (AST) that can be further processed into a circuit graph.

## Quick Start

```typescript
import { parse, tokenize } from '@/parser'

const source = `
[VCC]: net
[GND]: net
[R1]: resistor(10k)
[VCC --- R1.1]
[R1.2 --- GND]
`

// Parse directly to AST
const result = parse(source, 'circuit.circuit.md')

if (result.errors.length === 0) {
  console.log('Parsed successfully:', result.ast)
} else {
  console.error('Parse errors:', result.errors)
}
```

## API Reference

### `tokenize(source: string, filename?: string): LexerResult`

Converts source text into a stream of tokens.

**Parameters:**
- `source` - The circuit.md source text
- `filename` - Optional filename for error reporting (default: 'input')

**Returns:** `LexerResult`
- `tokens` - Array of `CircuitToken` objects
- `errors` - Array of `ParseError` objects

**Example:**
```typescript
import { tokenize } from '@/parser'

const result = tokenize('[R1]: resistor(10k)')
// result.tokens[0] = {
//   type: 'COMPONENT_DECLARATION',
//   ref: 'R1',
//   componentType: 'resistor',
//   params: ['10k'],
//   raw: '[R1]: resistor(10k)',
//   location: { file: 'input', line: 1, column: 1 }
// }
```

### `parse(source: string, filename?: string): ParseResult`

Parses source text into a complete AST.

**Parameters:**
- `source` - The circuit.md source text
- `filename` - Optional filename for error reporting

**Returns:** `ParseResult`
- `ast` - The `CircuitAST` object
- `errors` - Array of `ParseError` objects

### `resolve(ast: CircuitAST, options?: ResolveOptions): Promise<ResolveResult>`

Resolves sub-circuit references in an AST by loading and parsing referenced files.

**Parameters:**
- `ast` - The parsed AST with potential sub-circuit references
- `options` - Resolution options including file loader

**Returns:** `Promise<ResolveResult>`
- `ast` - Fully resolved AST with inlined sub-circuits
- `errors` - Array of resolution errors

**Example:**
```typescript
import { parse, resolve, createMapLoader } from '@/parser'

const files = new Map([
  ['main.circuit.md', '[U1]: @./power.circuit.md'],
  ['power.circuit.md', '[VCC]: net\n[GND]: net'],
])

const result = parse(files.get('main.circuit.md')!, 'main.circuit.md')
const resolved = await resolve(result.ast, {
  loader: createMapLoader(files),
})
```

## Token Types

| Type | Description | Example |
|------|-------------|---------|
| `NET_DECLARATION` | Net declaration | `[VCC]: net` |
| `COMPONENT_DECLARATION` | Component with type and params | `[R1]: resistor(10k)` |
| `SUBCIRCUIT_REFERENCE` | Reference to external file | `[U1]: @./power.circuit.md` |
| `CONNECTION` | Connection between endpoints | `[VCC --- R1.1]` |
| `INLINE_PASSIVE` | Inline component declaration | `[A --- 10k --- B]` |
| `PROPERTY` | Key-value property | `[voltage ==> 3.3V]` |
| `TEXT` | Non-circuit markdown content | `# Title` |
| `FRONTMATTER` | YAML frontmatter block | `---\nname: Circuit\n---` |
| `EOF` | End of file marker | - |

## AST Node Types

### NetNode

Represents a declared net (electrical connection point).

```typescript
interface NetNode {
  type: 'net'
  name: string      // e.g., 'VCC', 'GND', 'NODE1'
  location: SourceLocation
}
```

### ComponentNode

Represents a declared component.

```typescript
interface ComponentNode {
  type: 'component'
  ref: string           // e.g., 'R1', 'U1'
  componentType: string // e.g., 'resistor', 'esp32'
  params: string[]      // e.g., ['10k'], ['ESP32-WROOM-32']
  location: SourceLocation
}
```

### SubcircuitNode

Represents a reference to an external circuit file.

```typescript
interface SubcircuitNode {
  type: 'subcircuit'
  ref: string    // e.g., 'U1'
  path: string   // e.g., './power.circuit.md'
  resolved?: CircuitAST  // Populated after resolution
  location: SourceLocation
}
```

### ConnectionNode

Represents a connection between two endpoints.

```typescript
interface ConnectionNode {
  type: 'connection'
  from: Endpoint  // { ref: 'R1', pin: '1' } or { net: 'VCC' }
  to: Endpoint
  location: SourceLocation
}
```

### InlinePassiveNode

Represents an inline passive component (auto-generated).

```typescript
interface InlinePassiveNode {
  type: 'inline_passive'
  from: Endpoint
  to: Endpoint
  value: string       // e.g., '10k', '100nF'
  passiveType: 'resistor' | 'capacitor' | 'inductor' | 'fuse'
  generatedRef: string  // e.g., '_R1', '_C1'
  location: SourceLocation
}
```

## Error Handling

Parse errors include location information for helpful error messages:

```typescript
interface ParseError {
  message: string
  location: {
    file: string
    line: number
    column: number
  }
  severity: 'error' | 'warning'
}
```

**Example error handling:**
```typescript
const result = parse(source, filename)

for (const error of result.errors) {
  if (error.severity === 'error') {
    console.error(`${error.location.file}:${error.location.line}: ${error.message}`)
  } else {
    console.warn(`Warning at line ${error.location.line}: ${error.message}`)
  }
}
```

## Helper Functions

### `getComponentTypes(ast: CircuitAST): string[]`

Returns all unique component types used in the circuit.

### `getAllNets(ast: CircuitAST): string[]`

Returns all net names declared in the circuit.

### `parseEndpoint(str: string): Endpoint`

Parses an endpoint string like "R1.1" or "VCC" into an Endpoint object.
