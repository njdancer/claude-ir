import type { CircuitAST, ConnectionNode, InlinePassiveNode, Endpoint } from '@/parser'
import type { CircuitGraph } from '@/graph'
import type { ValidationIssue, ValidationResult, IssueSeverity, IssueCategory } from './types'

let issueCounter = 0

/**
 * Generate a unique issue ID
 */
function generateIssueId(category: IssueCategory): string {
  return `${category.toUpperCase()}-${++issueCounter}`
}

/**
 * Create a validation issue
 */
function createIssue(
  severity: IssueSeverity,
  category: IssueCategory,
  message: string,
  location: SourceLocation,
  relatedNodes?: string[],
  suggestion?: string
): ValidationIssue {
  return {
    id: generateIssueId(category),
    severity,
    category,
    message,
    location,
    relatedNodes,
    suggestion,
  }
}

/**
 * Validate references (nets and components) used in connections
 */
function validateReferences(ast: CircuitAST, issues: ValidationIssue[]): void {
  const declaredNets = new Set(ast.nets.keys())
  const declaredComponents = new Set(ast.components.keys())
  const declaredSubcircuits = new Set(ast.subcircuits.keys())

  // Track all endpoints used in connections
  const checkEndpoint = (endpoint: Endpoint, connection: ConnectionNode | InlinePassiveNode) => {
    if (endpoint.pin) {
      // This is a component.pin reference
      const componentRef = endpoint.ref
      if (
        !declaredComponents.has(componentRef) &&
        !declaredSubcircuits.has(componentRef) &&
        !isInlinePassiveRef(componentRef, ast)
      ) {
        issues.push(
          createIssue(
            'warning',
            'reference',
            `Component '${componentRef}' is used but not declared`,
            connection.location,
            [componentRef],
            `Add declaration: [${componentRef}]: <type>`
          )
        )
      }
    } else {
      // This is a net reference
      const netName = endpoint.ref
      if (
        !declaredNets.has(netName) &&
        !declaredComponents.has(netName) &&
        !declaredSubcircuits.has(netName) &&
        !isInlinePassiveRef(netName, ast)
      ) {
        issues.push(
          createIssue(
            'warning',
            'reference',
            `Net '${netName}' is used but not declared`,
            connection.location,
            [netName],
            `Add declaration: [${netName}]: net`
          )
        )
      }
    }
  }

  // Check all connections
  for (const conn of ast.connections) {
    checkEndpoint(conn.from, conn)
    checkEndpoint(conn.to, conn)
  }

  // Check inline passive endpoints
  for (const passive of ast.inlinePassives) {
    checkEndpoint(passive.from, passive)
    checkEndpoint(passive.to, passive)
  }
}

/**
 * Check if a reference is an inline passive reference
 */
function isInlinePassiveRef(ref: string, ast: CircuitAST): boolean {
  return ast.inlinePassives.some((p) => p.ref === ref)
}

/**
 * Validate for duplicate declarations
 * The parser already detects duplicates and stores them in ast.errors.
 * We convert these to validation issues.
 */
function validateDuplicates(ast: CircuitAST, issues: ValidationIssue[]): void {
  // Convert parser errors about duplicates to validation issues
  for (const error of ast.errors) {
    if (error.message.includes('Duplicate')) {
      const severity: IssueSeverity = error.severity === 'error' ? 'error' : 'warning'
      issues.push(
        createIssue(
          severity,
          'duplicate',
          error.message,
          error.location,
          undefined,
          'Use a unique name or reference designator'
        )
      )
    }
  }

  // Check for net/component name collisions
  for (const [name, net] of ast.nets) {
    if (ast.components.has(name)) {
      issues.push(
        createIssue(
          'error',
          'duplicate',
          `Name collision: '${name}' is declared as both a net and a component`,
          net.location,
          [name]
        )
      )
    }
  }
}

/**
 * Validate connectivity (floating nets, single connections)
 */
function validateConnectivity(ast: CircuitAST, graph: CircuitGraph, issues: ValidationIssue[]): void {
  // Count connections per net
  const netConnectionCounts = new Map<string, number>()

  // Initialize all declared nets with 0 connections
  for (const [name] of ast.nets) {
    netConnectionCounts.set(name, 0)
  }

  // Count connections from edges
  for (const edge of graph.edges) {
    const sourceNode = graph.nodes.get(edge.sourceId)
    const targetNode = graph.nodes.get(edge.targetId)

    if (sourceNode?.type === 'net') {
      const count = netConnectionCounts.get(sourceNode.label) ?? 0
      netConnectionCounts.set(sourceNode.label, count + 1)
    }
    if (targetNode?.type === 'net') {
      const count = netConnectionCounts.get(targetNode.label) ?? 0
      netConnectionCounts.set(targetNode.label, count + 1)
    }
  }

  // Check each declared net
  for (const [name, net] of ast.nets) {
    const count = netConnectionCounts.get(name) ?? 0

    if (count === 0) {
      // Floating net - declared but never used
      issues.push(
        createIssue(
          'warning',
          'connectivity',
          `Net '${name}' is declared but unused (floating)`,
          net.location,
          [name],
          'Remove the declaration or connect it'
        )
      )
    } else if (count === 1) {
      // Single connection - usually indicates a mistake
      issues.push(
        createIssue(
          'warning',
          'connectivity',
          `Net '${name}' has only a single connection`,
          net.location,
          [name],
          'Connect to another component or remove if unused'
        )
      )
    }
  }
}

/**
 * Group issues by file
 */
function groupByFile(issues: ValidationIssue[]): Map<string, ValidationIssue[]> {
  const byFile = new Map<string, ValidationIssue[]>()

  for (const issue of issues) {
    const file = issue.location.file
    if (!byFile.has(file)) {
      byFile.set(file, [])
    }
    byFile.get(file)!.push(issue)
  }

  return byFile
}

/**
 * Group issues by severity
 */
function groupBySeverity(issues: ValidationIssue[]): {
  error: ValidationIssue[]
  warning: ValidationIssue[]
  info: ValidationIssue[]
} {
  return {
    error: issues.filter((i) => i.severity === 'error'),
    warning: issues.filter((i) => i.severity === 'warning'),
    info: issues.filter((i) => i.severity === 'info'),
  }
}

/**
 * Validate a circuit AST and graph
 */
export function validate(ast: CircuitAST, graph: CircuitGraph): ValidationResult {
  // Reset counter for consistent IDs
  issueCounter = 0

  const issues: ValidationIssue[] = []

  // Run all validators
  validateDuplicates(ast, issues)
  validateReferences(ast, issues)
  validateConnectivity(ast, graph, issues)

  // Group results
  const byFile = groupByFile(issues)
  const bySeverity = groupBySeverity(issues)

  return {
    issues,
    byFile,
    bySeverity,
    hasErrors: bySeverity.error.length > 0,
    counts: {
      error: bySeverity.error.length,
      warning: bySeverity.warning.length,
      info: bySeverity.info.length,
      total: issues.length,
    },
  }
}
