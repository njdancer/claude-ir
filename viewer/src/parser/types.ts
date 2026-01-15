/**
 * Source location information for AST nodes
 */
export interface SourceLocation {
  file: string
  line: number
  column: number
}

/**
 * Token types for circuit.md lexer
 */
export type TokenType =
  | 'NET_DECLARATION' // [NAME]: net
  | 'COMPONENT_DECLARATION' // [REF]: type(params)
  | 'SUBCIRCUIT_REFERENCE' // [REF]: @./path
  | 'CONNECTION' // [A --- B]
  | 'INLINE_PASSIVE' // [A --- value --- B]
  | 'PROPERTY' // [key ==> value]
  | 'TEXT' // Regular markdown text
  | 'FRONTMATTER' // YAML frontmatter
  | 'EOF'

/**
 * Base token interface
 */
export interface Token {
  type: TokenType
  raw: string
  location: SourceLocation
}

/**
 * Net declaration token: [NAME]: net
 */
export interface NetDeclarationToken extends Token {
  type: 'NET_DECLARATION'
  name: string
}

/**
 * Component declaration token: [REF]: type(params)
 */
export interface ComponentDeclarationToken extends Token {
  type: 'COMPONENT_DECLARATION'
  ref: string
  componentType: string
  params: string[]
}

/**
 * Sub-circuit reference token: [REF]: @./path.circuit.md
 */
export interface SubcircuitReferenceToken extends Token {
  type: 'SUBCIRCUIT_REFERENCE'
  ref: string
  path: string
}

/**
 * Connection token: [A --- B]
 */
export interface ConnectionToken extends Token {
  type: 'CONNECTION'
  from: string
  to: string
}

/**
 * Inline passive token: [A --- value --- B]
 */
export interface InlinePassiveToken extends Token {
  type: 'INLINE_PASSIVE'
  from: string
  value: string
  to: string
  passiveType: 'resistor' | 'capacitor' | 'inductor' | 'fuse'
}

/**
 * Property token: [key ==> value]
 */
export interface PropertyToken extends Token {
  type: 'PROPERTY'
  key: string
  value: string
}

/**
 * Text token (non-circuit content)
 */
export interface TextToken extends Token {
  type: 'TEXT'
  content: string
}

/**
 * YAML frontmatter token
 */
export interface FrontmatterToken extends Token {
  type: 'FRONTMATTER'
  content: string
}

/**
 * End of file token
 */
export interface EOFToken extends Token {
  type: 'EOF'
}

/**
 * Union of all token types
 */
export type CircuitToken =
  | NetDeclarationToken
  | ComponentDeclarationToken
  | SubcircuitReferenceToken
  | ConnectionToken
  | InlinePassiveToken
  | PropertyToken
  | TextToken
  | FrontmatterToken
  | EOFToken

/**
 * Parse error with location
 */
export interface ParseError {
  message: string
  location: SourceLocation
  severity: 'error' | 'warning'
}

/**
 * Result of lexing a circuit.md file
 */
export interface LexerResult {
  tokens: CircuitToken[]
  errors: ParseError[]
}
