import { tokenize } from './lexer'
import type { ParseError, LexerResult } from './types'
import {
  type CircuitAST,
  type NetNode,
  type ComponentNode,
  type SubcircuitNode,
  type ConnectionNode,
  type InlinePassiveNode,
  type PropertyNode,
  type Frontmatter,
  createCircuitAST,
  parseEndpoint,
} from './ast'

/**
 * Counters for generating inline passive references
 */
interface InlinePassiveCounters {
  resistor: number
  capacitor: number
  inductor: number
  fuse: number
}

/**
 * Parse YAML frontmatter content into an object
 */
function parseFrontmatter(content: string): Frontmatter {
  const result: Frontmatter = {}

  // Simple YAML parser for common keys
  const lines = content.split('\n')
  let currentKey: string | null = null
  let multilineValue = ''
  let inMultiline = false

  for (const line of lines) {
    // Check for multiline indicator
    if (inMultiline) {
      if (line.startsWith('  ') || line.trim() === '') {
        multilineValue += (multilineValue ? '\n' : '') + line.replace(/^ {2}/, '')
        continue
      } else {
        // End of multiline
        if (currentKey) {
          result[currentKey] = multilineValue.trim()
        }
        inMultiline = false
        multilineValue = ''
      }
    }

    // Check for key: value
    const keyMatch = line.match(/^([a-z_][a-z0-9_]*):\s*(.*)$/i)
    if (keyMatch) {
      currentKey = keyMatch[1]
      const value = keyMatch[2].trim()

      if (value === '|' || value === '>') {
        // Start multiline
        inMultiline = true
        multilineValue = ''
      } else if (value) {
        result[currentKey] = value
      }
    }
  }

  // Handle trailing multiline
  if (inMultiline && currentKey) {
    result[currentKey] = multilineValue.trim()
  }

  return result
}

/**
 * Build AST from lexer tokens
 */
function buildAST(lexerResult: LexerResult, filename: string): CircuitAST {
  const ast = createCircuitAST(filename)
  const counters: InlinePassiveCounters = {
    resistor: 0,
    capacitor: 0,
    inductor: 0,
    fuse: 0,
  }

  // Copy lexer errors
  ast.errors.push(...lexerResult.errors)

  for (const token of lexerResult.tokens) {
    switch (token.type) {
      case 'FRONTMATTER':
        ast.frontmatter = parseFrontmatter(token.content)
        break

      case 'NET_DECLARATION': {
        const netNode: NetNode = {
          kind: 'net',
          name: token.name,
          location: token.location,
        }

        // Check for duplicate
        if (ast.nets.has(token.name)) {
          ast.errors.push({
            message: `Duplicate net declaration: ${token.name}`,
            location: token.location,
            severity: 'warning',
          })
        }

        ast.nets.set(token.name, netNode)
        break
      }

      case 'COMPONENT_DECLARATION': {
        const componentNode: ComponentNode = {
          kind: 'component',
          ref: token.ref,
          componentType: token.componentType,
          params: token.params,
          location: token.location,
        }

        // Check for duplicate
        if (ast.components.has(token.ref) || ast.subcircuits.has(token.ref)) {
          ast.errors.push({
            message: `Duplicate reference designator: ${token.ref}`,
            location: token.location,
            severity: 'error',
          })
        }

        ast.components.set(token.ref, componentNode)
        break
      }

      case 'SUBCIRCUIT_REFERENCE': {
        const subcircuitNode: SubcircuitNode = {
          kind: 'subcircuit',
          ref: token.ref,
          path: token.path,
          location: token.location,
        }

        // Check for duplicate
        if (ast.components.has(token.ref) || ast.subcircuits.has(token.ref)) {
          ast.errors.push({
            message: `Duplicate reference designator: ${token.ref}`,
            location: token.location,
            severity: 'error',
          })
        }

        ast.subcircuits.set(token.ref, subcircuitNode)
        break
      }

      case 'CONNECTION': {
        const connectionNode: ConnectionNode = {
          kind: 'connection',
          from: parseEndpoint(token.from),
          to: parseEndpoint(token.to),
          location: token.location,
        }

        ast.connections.push(connectionNode)
        break
      }

      case 'INLINE_PASSIVE': {
        // Generate reference
        counters[token.passiveType]++
        const prefix =
          token.passiveType === 'resistor'
            ? 'R'
            : token.passiveType === 'capacitor'
              ? 'C'
              : token.passiveType === 'inductor'
                ? 'L'
                : 'F'
        const ref = `_${prefix}${counters[token.passiveType]}`

        const inlineNode: InlinePassiveNode = {
          kind: 'inline_passive',
          ref,
          passiveType: token.passiveType,
          value: token.value,
          from: parseEndpoint(token.from),
          to: parseEndpoint(token.to),
          location: token.location,
        }

        ast.inlinePassives.push(inlineNode)
        break
      }

      case 'PROPERTY': {
        const propertyNode: PropertyNode = {
          kind: 'property',
          key: token.key,
          value: token.value,
          location: token.location,
        }

        ast.properties.push(propertyNode)
        break
      }

      case 'TEXT':
      case 'EOF':
        // Ignore
        break
    }
  }

  return ast
}

/**
 * Parse a circuit.md file content into an AST
 */
export function parse(content: string, filename: string): CircuitAST {
  const lexerResult = tokenize(content, filename)
  return buildAST(lexerResult, filename)
}

/**
 * Result of parsing multiple files
 */
export interface ParseResult {
  /** Main circuit AST */
  ast: CircuitAST
  /** All parse errors across all files */
  errors: ParseError[]
}
