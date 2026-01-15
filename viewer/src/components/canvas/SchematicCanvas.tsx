import { useRef, useCallback, useState } from 'react'
import type { CircuitGraph, ComponentGraphNode, NetGraphNode } from '@/graph'
import type { LayoutResult } from '@/layout'
import type { SymbolRenderContext } from '@/symbols'
import { createSymbolRegistry, getSymbolForType } from '@/symbols'
import { SymbolRenderer } from './SymbolRenderer'
import { WireRenderer, NetLabel } from './WireRenderer'

interface SchematicCanvasProps {
  graph: CircuitGraph | null
  layout: LayoutResult | null
  selectedNodes: Set<string>
  hoveredNode: string | null
  highlightedNodes?: Set<string>
  showNetLabels?: boolean
  showValues?: boolean
  showGrid?: boolean
  gridSize?: number
  zoom: number
  panX: number
  panY: number
  onNodeClick?: (nodeId: string) => void
  onNodeHover?: (nodeId: string | null) => void
  onPan?: (deltaX: number, deltaY: number) => void
  onZoom?: (delta: number, centerX: number, centerY: number) => void
}

/**
 * Main schematic canvas component
 */
export function SchematicCanvas({
  graph,
  layout,
  selectedNodes,
  hoveredNode,
  highlightedNodes = new Set(),
  showNetLabels = true,
  showValues = true,
  showGrid = true,
  gridSize = 10,
  zoom,
  panX,
  panY,
  onNodeClick,
  onNodeHover,
  onPan,
  onZoom,
}: SchematicCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [lastMousePos, setLastMousePos] = useState({ x: 0, y: 0 })

  // Create symbol registry
  const registry = createSymbolRegistry()

  // Mouse event handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button === 0) {
        // Left click - start panning
        setIsDragging(true)
        setLastMousePos({ x: e.clientX, y: e.clientY })
      }
    },
    []
  )

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging && onPan) {
        const deltaX = e.clientX - lastMousePos.x
        const deltaY = e.clientY - lastMousePos.y
        onPan(deltaX, deltaY)
        setLastMousePos({ x: e.clientX, y: e.clientY })
      }
    },
    [isDragging, lastMousePos, onPan]
  )

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (onZoom && svgRef.current) {
        e.preventDefault()
        const rect = svgRef.current.getBoundingClientRect()
        const centerX = e.clientX - rect.left
        const centerY = e.clientY - rect.top
        const delta = e.deltaY > 0 ? -0.1 : 0.1
        onZoom(delta, centerX, centerY)
      }
    },
    [onZoom]
  )

  // Calculate viewBox based on layout bounds
  const viewBox = layout
    ? `${layout.bounds.x - panX / zoom} ${layout.bounds.y - panY / zoom} ${layout.bounds.width / zoom} ${layout.bounds.height / zoom}`
    : '0 0 800 600'

  if (!graph || !layout) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-50 text-slate-400">
        <div className="text-center">
          <p className="text-lg">No circuit loaded</p>
          <p className="text-sm">Drop a .circuit.md file to view</p>
        </div>
      </div>
    )
  }

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      viewBox={viewBox}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
      style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
    >
      {/* Background grid */}
      {showGrid && (
        <defs>
          <pattern
            id="grid"
            width={gridSize}
            height={gridSize}
            patternUnits="userSpaceOnUse"
          >
            <path
              d={`M ${gridSize} 0 L 0 0 0 ${gridSize}`}
              fill="none"
              stroke="var(--color-grid, #e2e8f0)"
              strokeWidth="0.5"
            />
          </pattern>
        </defs>
      )}

      {showGrid && (
        <rect
          x={layout.bounds.x - 100}
          y={layout.bounds.y - 100}
          width={layout.bounds.width + 200}
          height={layout.bounds.height + 200}
          fill="url(#grid)"
        />
      )}

      {/* Wires (render first, behind symbols) */}
      <g className="wires">
        {layout.edges.map((edge) => (
          <WireRenderer
            key={edge.id}
            edge={edge}
            selected={selectedNodes.has(edge.sourceId) || selectedNodes.has(edge.targetId)}
            highlighted={highlightedNodes.has(edge.sourceId) || highlightedNodes.has(edge.targetId)}
          />
        ))}
      </g>

      {/* Symbols */}
      <g className="symbols">
        {Array.from(layout.nodes.entries()).map(([nodeId, posNode]) => {
          const graphNode = graph.nodes.get(nodeId)
          if (!graphNode) return null

          // Get symbol for this node
          let symbol = null
          let value: string | undefined

          if (graphNode.type === 'component') {
            const compNode = graphNode as ComponentGraphNode
            symbol = getSymbolForType(registry, compNode.componentType)
            value = compNode.params[0]
          } else if (graphNode.type === 'net') {
            // For nets, just show a label
            const netNode = graphNode as NetGraphNode
            if (showNetLabels) {
              return (
                <NetLabel
                  key={nodeId}
                  x={posNode.position.x}
                  y={posNode.position.y}
                  name={netNode.name}
                  selected={selectedNodes.has(nodeId)}
                />
              )
            }
            return null
          }

          if (!symbol) return null

          const context: SymbolRenderContext = {
            x: posNode.position.x,
            y: posNode.position.y,
            orientation: posNode.orientation,
            scale: 1,
            reference: graphNode.label.split(':')[0], // Extract ref from "R1: resistor"
            value: showValues ? value : undefined,
            selected: selectedNodes.has(nodeId),
            hovered: hoveredNode === nodeId,
            highlighted: highlightedNodes.has(nodeId),
          }

          return (
            <SymbolRenderer
              key={nodeId}
              symbol={symbol.definition}
              context={context}
              onClick={() => onNodeClick?.(nodeId)}
              onMouseEnter={() => onNodeHover?.(nodeId)}
              onMouseLeave={() => onNodeHover?.(null)}
            />
          )
        })}
      </g>
    </svg>
  )
}
