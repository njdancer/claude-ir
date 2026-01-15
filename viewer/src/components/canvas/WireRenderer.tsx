import type { RoutedEdge } from '@/layout'

interface WireRendererProps {
  edge: RoutedEdge
  selected?: boolean
  highlighted?: boolean
  showJunctions?: boolean
}

/**
 * Renders a wire (routed edge) as SVG path
 */
export function WireRenderer({
  edge,
  selected = false,
  highlighted = false,
  showJunctions = true,
}: WireRendererProps) {
  if (edge.waypoints.length < 2) return null

  // Build path from waypoints
  const pathData = edge.waypoints
    .map((wp, i) => (i === 0 ? `M ${wp.x} ${wp.y}` : `L ${wp.x} ${wp.y}`))
    .join(' ')

  // Determine stroke color based on state
  const getStrokeColor = () => {
    if (selected) return 'var(--color-selected, #3b82f6)'
    if (highlighted) return 'var(--color-highlight, #22c55e)'
    return 'var(--color-wire, #64748b)'
  }

  const strokeColor = getStrokeColor()

  return (
    <g className="wire">
      {/* Wire path */}
      <path
        d={pathData}
        stroke={strokeColor}
        strokeWidth={selected ? 3 : 2}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Junction dots */}
      {showJunctions &&
        edge.waypoints
          .filter((wp) => wp.isJunction)
          .map((wp, index) => (
            <circle key={index} cx={wp.x} cy={wp.y} r={4} fill={strokeColor} />
          ))}
    </g>
  )
}

/**
 * Renders a net label
 */
export function NetLabel({
  x,
  y,
  name,
  selected = false,
}: {
  x: number
  y: number
  name: string
  selected?: boolean
}) {
  return (
    <g transform={`translate(${x}, ${y})`}>
      <rect
        x={-4}
        y={-10}
        width={name.length * 7 + 8}
        height={16}
        fill="var(--color-bg, white)"
        stroke={selected ? 'var(--color-selected, #3b82f6)' : 'var(--color-border, #cbd5e1)'}
        strokeWidth={1}
        rx={2}
      />
      <text
        x={name.length * 3.5}
        y={2}
        textAnchor="middle"
        fontSize="11"
        fontFamily="monospace"
        fill="var(--color-text, #334155)"
      >
        {name}
      </text>
    </g>
  )
}
