import type {
  CircuitToken,
  LexerResult,
  ParseError,
  SourceLocation,
  NetDeclarationToken,
  ComponentDeclarationToken,
  SubcircuitReferenceToken,
  ConnectionToken,
  InlinePassiveToken,
  PropertyToken,
  TextToken,
  FrontmatterToken,
} from './types'

/**
 * Regex patterns for circuit.md syntax
 */
const PATTERNS = {
  // [NAME]: net
  NET_DECLARATION: /^\[([A-Za-z_][A-Za-z0-9_]*)\]:\s*net\b/,

  // [REF]: @./path
  SUBCIRCUIT_REFERENCE: /^\[([A-Za-z_][A-Za-z0-9_]*)\]:\s*@(\S+)/,

  // [REF]: type(params) or [REF]: type
  COMPONENT_DECLARATION: /^\[([A-Za-z_][A-Za-z0-9_]*)\]:\s*([a-z_][a-z0-9_]*)(?:\(([^)]*)\))?/i,

  // [A --- value --- B] (inline passive)
  INLINE_PASSIVE:
    /^\[([^\[\]]+?)\s+---\s+(\d+(?:\.\d+)?[kKmMµunp]?[ΩRFHAfAhΩ]?)\s+---\s+([^\[\]]+?)\]/,

  // [A --- B] (connection)
  CONNECTION: /^\[([^\[\]]+?)\s+---\s+([^\[\]]+?)\]/,

  // [key ==> value]
  PROPERTY: /^\[([^\[\]=]+?)\s*==>\s*([^\[\]]+?)\]/,

  // YAML frontmatter
  FRONTMATTER: /^---\n([\s\S]*?)\n---/,

  // Value suffixes for determining passive type
  RESISTOR_VALUE: /[ΩR]$/i,
  CAPACITOR_VALUE: /F$/i,
  INDUCTOR_VALUE: /H$/i,
  FUSE_VALUE: /A$/i,
  // Also detect resistors by numeric patterns without suffix (k, M, m patterns)
  RESISTOR_NUMERIC: /^\d+(?:\.\d+)?[kKmM]?\d*$/,
}

/**
 * Determine passive type from value string
 */
function getPassiveType(value: string): 'resistor' | 'capacitor' | 'inductor' | 'fuse' {
  if (PATTERNS.CAPACITOR_VALUE.test(value)) return 'capacitor'
  if (PATTERNS.INDUCTOR_VALUE.test(value)) return 'inductor'
  if (PATTERNS.FUSE_VALUE.test(value) && !PATTERNS.CAPACITOR_VALUE.test(value)) return 'fuse'
  // Default to resistor for Ω, R suffix, or numeric values like 4k7, 10k
  return 'resistor'
}

/**
 * Parse component parameters from string
 */
function parseParams(paramsStr: string | undefined): string[] {
  if (!paramsStr) return []
  return paramsStr.split(',').map((p) => p.trim())
}

/**
 * Create a source location
 */
function createLocation(file: string, line: number, column: number): SourceLocation {
  return { file, line, column }
}

/**
 * Tokenize a circuit.md file
 */
export function tokenize(input: string, filename: string): LexerResult {
  const tokens: CircuitToken[] = []
  const errors: ParseError[] = []

  let pos = 0
  let line = 1
  let lineStart = 0

  // Helper to get current column
  const getColumn = () => pos - lineStart + 1

  // Helper to advance past newlines
  const advanceNewlines = () => {
    while (pos < input.length && (input[pos] === '\n' || input[pos] === '\r')) {
      if (input[pos] === '\n') {
        line++
        lineStart = pos + 1
      }
      pos++
    }
  }

  // Check for YAML frontmatter at start
  if (input.startsWith('---\n')) {
    const match = input.match(PATTERNS.FRONTMATTER)
    if (match) {
      const token: FrontmatterToken = {
        type: 'FRONTMATTER',
        raw: match[0],
        content: match[1],
        location: createLocation(filename, 1, 1),
      }
      tokens.push(token)
      pos = match[0].length
      // Update line count
      const newlines = match[0].split('\n').length - 1
      line += newlines
      lineStart = pos - (match[0].length - match[0].lastIndexOf('\n') - 1)
    }
  }

  // Main tokenization loop
  while (pos < input.length) {
    // Skip whitespace (but track newlines)
    if (input[pos] === '\n') {
      line++
      pos++
      lineStart = pos
      continue
    }
    if (input[pos] === '\r') {
      pos++
      continue
    }
    if (input[pos] === ' ' || input[pos] === '\t') {
      pos++
      continue
    }

    // Look for bracket syntax
    if (input[pos] === '[') {
      const remaining = input.slice(pos)
      const startColumn = getColumn()
      const startLine = line

      // Check for unclosed bracket
      const closeBracket = remaining.indexOf(']')
      if (closeBracket === -1) {
        errors.push({
          message: 'Unclosed bracket - expected ]',
          location: createLocation(filename, startLine, startColumn),
          severity: 'error',
        })
        pos++
        continue
      }

      // Try to match patterns in order of specificity
      let matched = false

      // Net declaration
      const netMatch = remaining.match(PATTERNS.NET_DECLARATION)
      if (netMatch) {
        const token: NetDeclarationToken = {
          type: 'NET_DECLARATION',
          raw: netMatch[0],
          name: netMatch[1],
          location: createLocation(filename, startLine, startColumn),
        }
        tokens.push(token)
        pos += netMatch[0].length
        matched = true
      }

      // Subcircuit reference (must check before component)
      if (!matched) {
        const subMatch = remaining.match(PATTERNS.SUBCIRCUIT_REFERENCE)
        if (subMatch) {
          const token: SubcircuitReferenceToken = {
            type: 'SUBCIRCUIT_REFERENCE',
            raw: subMatch[0],
            ref: subMatch[1],
            path: subMatch[2],
            location: createLocation(filename, startLine, startColumn),
          }
          tokens.push(token)
          pos += subMatch[0].length
          matched = true
        }
      }

      // Component declaration
      if (!matched) {
        const compMatch = remaining.match(PATTERNS.COMPONENT_DECLARATION)
        if (compMatch && !remaining.match(/^\[[^\]]+\s+---/)) {
          const token: ComponentDeclarationToken = {
            type: 'COMPONENT_DECLARATION',
            raw: compMatch[0],
            ref: compMatch[1],
            componentType: compMatch[2],
            params: parseParams(compMatch[3]),
            location: createLocation(filename, startLine, startColumn),
          }
          tokens.push(token)
          pos += compMatch[0].length
          matched = true
        }
      }

      // Property
      if (!matched) {
        const propMatch = remaining.match(PATTERNS.PROPERTY)
        if (propMatch) {
          const token: PropertyToken = {
            type: 'PROPERTY',
            raw: propMatch[0],
            key: propMatch[1].trim(),
            value: propMatch[2].trim(),
            location: createLocation(filename, startLine, startColumn),
          }
          tokens.push(token)
          pos += propMatch[0].length
          matched = true
        }
      }

      // Inline passive (must check before connection)
      if (!matched) {
        const passiveMatch = remaining.match(PATTERNS.INLINE_PASSIVE)
        if (passiveMatch) {
          const token: InlinePassiveToken = {
            type: 'INLINE_PASSIVE',
            raw: passiveMatch[0],
            from: passiveMatch[1].trim(),
            value: passiveMatch[2],
            to: passiveMatch[3].trim(),
            passiveType: getPassiveType(passiveMatch[2]),
            location: createLocation(filename, startLine, startColumn),
          }
          tokens.push(token)
          pos += passiveMatch[0].length
          matched = true
        }
      }

      // Connection
      if (!matched) {
        const connMatch = remaining.match(PATTERNS.CONNECTION)
        if (connMatch) {
          const token: ConnectionToken = {
            type: 'CONNECTION',
            raw: connMatch[0],
            from: connMatch[1].trim(),
            to: connMatch[2].trim(),
            location: createLocation(filename, startLine, startColumn),
          }
          tokens.push(token)
          pos += connMatch[0].length
          matched = true
        }
      }

      // If no pattern matched, treat as text
      if (!matched) {
        pos++
      }
    } else {
      // Non-bracket content - skip for now (we're focused on circuit syntax)
      // In a full implementation, we might collect this as TEXT tokens
      pos++
    }
  }

  // Add EOF token
  tokens.push({
    type: 'EOF',
    raw: '',
    location: createLocation(filename, line, getColumn()),
  })

  return { tokens, errors }
}
