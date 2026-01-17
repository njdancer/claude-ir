import { memo } from 'react'
import type { SymbolDefinition, SymbolRenderContext } from '@/symbols'

interface SymbolRendererProps {
  symbol: SymbolDefinition
  context: SymbolRenderContext
  onClick?: () => void
  onMouseEnter?: () => void
  onMouseLeave?: () => void
}

/**
 * Renders a single schematic symbol as SVG
 * Memoized to prevent unnecessary re-renders when parent updates
 */
export const SymbolRenderer = memo(function SymbolRenderer({
  symbol,
  context,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: SymbolRendererProps) {
  const { x, y, orientation, scale, reference, value, selected, hovered, highlighted } = context

  // Calculate transform
  const transform = `translate(${x}, ${y}) rotate(${orientation}) scale(${scale})`

  // Determine stroke color based on state
  const getStrokeColor = () => {
    if (selected) return 'var(--color-selected, #3b82f6)'
    if (hovered) return 'var(--color-hover, #60a5fa)'
    if (highlighted) return 'var(--color-highlight, #22c55e)'
    return 'currentColor'
  }

  const strokeColor = getStrokeColor()

  return (
    <g
      transform={transform}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className="symbol cursor-pointer"
      style={{ pointerEvents: 'all' }}
    >
      {/* Symbol paths */}
      {symbol.paths.map((path, index) => (
        <path
          key={index}
          d={path.d}
          stroke={path.stroke ?? strokeColor}
          strokeWidth={path.strokeWidth ?? 2}
          fill={path.fill ?? 'none'}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}

      {/* Reference designator label */}
      <text
        x={0}
        y={-symbol.height / 2 - 8}
        textAnchor="middle"
        fontSize="12"
        fontFamily="monospace"
        fill={strokeColor}
      >
        {reference}
      </text>

      {/* Value label (if applicable) */}
      {symbol.hasValueLabel && value && (
        <text
          x={0}
          y={symbol.height / 2 + 14}
          textAnchor="middle"
          fontSize="10"
          fontFamily="monospace"
          fill="currentColor"
          opacity={0.7}
        >
          {value}
        </text>
      )}

      {/* Hover/selection highlight */}
      {(selected || hovered) && (
        <rect
          x={-symbol.width / 2 - 5}
          y={-symbol.height / 2 - 5}
          width={symbol.width + 10}
          height={symbol.height + 10}
          fill="none"
          stroke={strokeColor}
          strokeWidth={1}
          strokeDasharray={selected ? 'none' : '4 2'}
          opacity={0.5}
          rx={4}
        />
      )}
    </g>
  )
})
