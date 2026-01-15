import type { SourceLocation } from '@/parser'

/**
 * Validation issue severity
 */
export type IssueSeverity = 'error' | 'warning' | 'info'

/**
 * Validation issue category
 */
export type IssueCategory = 'syntax' | 'reference' | 'connectivity' | 'duplicate'

/**
 * A validation issue found in the circuit
 */
export interface ValidationIssue {
  /** Unique issue ID */
  id: string
  /** Issue severity */
  severity: IssueSeverity
  /** Issue category */
  category: IssueCategory
  /** Human-readable message */
  message: string
  /** Location in source file */
  location: SourceLocation
  /** Related node IDs (if applicable) */
  relatedNodes?: string[]
  /** Suggested fix (if applicable) */
  suggestion?: string
}

/**
 * Result of validating a circuit
 */
export interface ValidationResult {
  /** All issues found */
  issues: ValidationIssue[]
  /** Issues grouped by file */
  byFile: Map<string, ValidationIssue[]>
  /** Issues grouped by severity */
  bySeverity: {
    error: ValidationIssue[]
    warning: ValidationIssue[]
    info: ValidationIssue[]
  }
  /** Whether any errors were found */
  hasErrors: boolean
  /** Total counts */
  counts: {
    error: number
    warning: number
    info: number
    total: number
  }
}
