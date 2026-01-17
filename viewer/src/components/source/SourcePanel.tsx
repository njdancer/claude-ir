import { useMemo, useEffect, useRef } from 'react'

interface SourcePanelProps {
  /** Source content to display */
  content: string | null
  /** Line to highlight (optional) */
  highlightLine?: number
  /** Callback when a line is clicked */
  onLineClick?: (line: number) => void
}

/**
 * Panel for viewing circuit.md source code
 */
export function SourcePanel({ content, highlightLine, onLineClick }: SourcePanelProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const highlightedRowRef = useRef<HTMLTableRowElement>(null)

  const lines = useMemo(() => {
    if (!content) return []
    return content.split('\n')
  }, [content])

  // Scroll to highlighted line when it changes
  useEffect(() => {
    if (highlightLine && highlightedRowRef.current && containerRef.current) {
      highlightedRowRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  }, [highlightLine])

  if (!content) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <p className="text-sm text-slate-500">No source loaded</p>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="h-full overflow-auto font-mono text-xs">
      <table className="w-full border-collapse">
        <tbody>
          {lines.map((line, index) => {
            const lineNum = index + 1
            const isHighlighted = highlightLine === lineNum

            return (
              <tr
                key={lineNum}
                ref={isHighlighted ? highlightedRowRef : undefined}
                className={`${isHighlighted ? 'bg-yellow-100' : 'hover:bg-slate-50'} cursor-pointer`}
                onClick={() => onLineClick?.(lineNum)}
              >
                <td className="select-none text-right pr-3 pl-2 text-slate-400 border-r border-slate-200 bg-slate-50 w-10">
                  {lineNum}
                </td>
                <td className="pl-3 pr-2 whitespace-pre text-slate-700">
                  {highlightSyntax(line)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Simple syntax highlighting for circuit.md
 */
function highlightSyntax(line: string): React.ReactNode {
  // YAML frontmatter delimiters
  if (line === '---') {
    return <span className="text-purple-600">{line}</span>
  }

  // Headers
  if (line.startsWith('#')) {
    return <span className="text-blue-600 font-semibold">{line}</span>
  }

  // Net declaration: [NET_NAME]: net
  const netMatch = line.match(/^(\[)([^\]]+)(\]: net)$/)
  if (netMatch) {
    return (
      <>
        <span className="text-slate-500">{netMatch[1]}</span>
        <span className="text-green-600 font-medium">{netMatch[2]}</span>
        <span className="text-purple-600">{netMatch[3]}</span>
      </>
    )
  }

  // Sub-circuit reference: [REF]: @./path.circuit.md
  const subcircuitMatch = line.match(/^(\[)([^\]]+)(\]: )(@\.\/[^\s]+)$/)
  if (subcircuitMatch) {
    return (
      <>
        <span className="text-slate-500">{subcircuitMatch[1]}</span>
        <span className="text-orange-600 font-medium">{subcircuitMatch[2]}</span>
        <span className="text-slate-500">{subcircuitMatch[3]}</span>
        <span className="text-cyan-600">{subcircuitMatch[4]}</span>
      </>
    )
  }

  // Component declaration: [REF]: type(params)
  const componentMatch = line.match(/^(\[)([^\]]+)(\]: )([a-zA-Z_][a-zA-Z0-9_-]*)(\([^)]*\))?$/)
  if (componentMatch) {
    return (
      <>
        <span className="text-slate-500">{componentMatch[1]}</span>
        <span className="text-orange-600 font-medium">{componentMatch[2]}</span>
        <span className="text-slate-500">{componentMatch[3]}</span>
        <span className="text-blue-600">{componentMatch[4]}</span>
        {componentMatch[5] && <span className="text-slate-600">{componentMatch[5]}</span>}
      </>
    )
  }

  // Connection: [A --- B] or [A --- value --- B]
  const connectionMatch = line.match(/^(\[)([^\]]+)(\])$/)
  if (connectionMatch && connectionMatch[2].includes('---')) {
    const parts = connectionMatch[2].split('---').map(p => p.trim())
    return (
      <>
        <span className="text-slate-500">[</span>
        {parts.map((part, i) => (
          <span key={i}>
            {i > 0 && <span className="text-purple-500"> --- </span>}
            <span className="text-teal-600">{part}</span>
          </span>
        ))}
        <span className="text-slate-500">]</span>
      </>
    )
  }

  // Property: [key ==> value]
  const propertyMatch = line.match(/^(\[)([^\]]+)(==>)([^\]]+)(\])$/)
  if (propertyMatch) {
    return (
      <>
        <span className="text-slate-500">{propertyMatch[1]}</span>
        <span className="text-amber-600">{propertyMatch[2]}</span>
        <span className="text-purple-500">{propertyMatch[3]}</span>
        <span className="text-slate-600">{propertyMatch[4]}</span>
        <span className="text-slate-500">{propertyMatch[5]}</span>
      </>
    )
  }

  // YAML key: value in frontmatter (simple detection)
  const yamlMatch = line.match(/^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*)(:\s*)(.*)$/)
  if (yamlMatch && !line.includes('[') && !line.includes('#')) {
    return (
      <>
        <span>{yamlMatch[1]}</span>
        <span className="text-blue-600">{yamlMatch[2]}</span>
        <span className="text-slate-500">{yamlMatch[3]}</span>
        <span className="text-green-700">{yamlMatch[4]}</span>
      </>
    )
  }

  // Comments (lines starting with spaces + text that could be markdown)
  if (line.match(/^\s*[A-Z]/) || line.match(/^\s+-\s/)) {
    return <span className="text-slate-500">{line}</span>
  }

  // Default
  return line
}
