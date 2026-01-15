import { AlertCircle, AlertTriangle, Info, ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import type { ValidationResult, ValidationIssue } from '@/validation'
import { cn } from '@/lib/utils'

interface ValidationPanelProps {
  validation: ValidationResult | null
  onIssueClick?: (issue: ValidationIssue) => void
}

/**
 * Panel displaying validation issues
 */
export function ValidationPanel({ validation, onIssueClick }: ValidationPanelProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['error']))

  if (!validation) {
    return (
      <div className="p-4 text-center text-slate-400">
        <p>No validation data</p>
      </div>
    )
  }

  if (validation.issues.length === 0) {
    return (
      <div className="p-4 text-center text-green-600">
        <div className="flex items-center justify-center gap-2">
          <div className="h-3 w-3 rounded-full bg-green-500" />
          <span>No issues found</span>
        </div>
      </div>
    )
  }

  const toggleCategory = (category: string) => {
    const newSet = new Set(expandedCategories)
    if (newSet.has(category)) {
      newSet.delete(category)
    } else {
      newSet.add(category)
    }
    setExpandedCategories(newSet)
  }

  // Group issues by category
  const byCategory = new Map<string, ValidationIssue[]>()
  for (const issue of validation.issues) {
    const existing = byCategory.get(issue.category) || []
    existing.push(issue)
    byCategory.set(issue.category, existing)
  }

  return (
    <div className="space-y-2 p-4">
      {/* Summary */}
      <div className="flex items-center gap-4 text-sm">
        {validation.counts.error > 0 && (
          <span className="flex items-center gap-1 text-red-600">
            <AlertCircle className="h-4 w-4" />
            {validation.counts.error} error{validation.counts.error !== 1 ? 's' : ''}
          </span>
        )}
        {validation.counts.warning > 0 && (
          <span className="flex items-center gap-1 text-amber-600">
            <AlertTriangle className="h-4 w-4" />
            {validation.counts.warning} warning{validation.counts.warning !== 1 ? 's' : ''}
          </span>
        )}
        {validation.counts.info > 0 && (
          <span className="flex items-center gap-1 text-blue-600">
            <Info className="h-4 w-4" />
            {validation.counts.info} info
          </span>
        )}
      </div>

      {/* Issues by category */}
      <div className="space-y-1">
        {Array.from(byCategory.entries()).map(([category, issues]) => {
          const isExpanded = expandedCategories.has(category)
          const errorCount = issues.filter((i) => i.severity === 'error').length
          const warningCount = issues.filter((i) => i.severity === 'warning').length

          return (
            <div key={category} className="rounded border">
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-sm font-medium hover:bg-slate-50"
                onClick={() => toggleCategory(category)}
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <span className="capitalize">{category}</span>
                <span className="ml-auto text-xs text-slate-400">
                  {errorCount > 0 && <span className="text-red-500">{errorCount}E</span>}
                  {errorCount > 0 && warningCount > 0 && ' '}
                  {warningCount > 0 && <span className="text-amber-500">{warningCount}W</span>}
                </span>
              </button>

              {isExpanded && (
                <div className="border-t">
                  {issues.map((issue, idx) => (
                    <IssueRow key={idx} issue={issue} onClick={() => onIssueClick?.(issue)} />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface IssueRowProps {
  issue: ValidationIssue
  onClick?: () => void
}

function IssueRow({ issue, onClick }: IssueRowProps) {
  const Icon =
    issue.severity === 'error'
      ? AlertCircle
      : issue.severity === 'warning'
        ? AlertTriangle
        : Info

  const colorClass =
    issue.severity === 'error'
      ? 'text-red-600'
      : issue.severity === 'warning'
        ? 'text-amber-600'
        : 'text-blue-600'

  return (
    <button
      className={cn(
        'flex w-full items-start gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50',
        onClick && 'cursor-pointer'
      )}
      onClick={onClick}
    >
      <Icon className={cn('mt-0.5 h-4 w-4 flex-shrink-0', colorClass)} />
      <div className="flex-1 min-w-0">
        <p className="break-words">{issue.message}</p>
        {issue.location && (
          <p className="text-xs text-slate-400">
            Line {issue.location.line}
            {issue.location.column && `:${issue.location.column}`}
          </p>
        )}
      </div>
    </button>
  )
}
