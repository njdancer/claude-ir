import { Button } from '@/components/ui/button'
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Grid3X3,
  Eye,
  EyeOff,
  Settings,
} from 'lucide-react'

interface ToolbarProps {
  zoom: number
  showGrid: boolean
  showNetLabels: boolean
  showValues: boolean
  onZoomIn: () => void
  onZoomOut: () => void
  onZoomReset: () => void
  onToggleGrid: () => void
  onToggleNetLabels: () => void
  onToggleValues: () => void
  onOpenSettings: () => void
}

/**
 * Toolbar with view controls
 */
export function Toolbar({
  zoom,
  showGrid,
  showNetLabels,
  showValues,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onToggleGrid,
  onToggleNetLabels,
  onToggleValues,
  onOpenSettings,
}: ToolbarProps) {
  const zoomPercent = Math.round(zoom * 100)

  return (
    <div className="flex items-center gap-2 p-2 border-b bg-white">
      {/* Zoom controls */}
      <div className="flex items-center gap-1 border-r pr-2 mr-2">
        <Button variant="ghost" size="icon" onClick={onZoomOut} title="Zoom out">
          <ZoomOut className="h-4 w-4" />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={onZoomReset}
          className="min-w-[60px] font-mono text-sm"
          title="Reset zoom"
        >
          {zoomPercent}%
        </Button>

        <Button variant="ghost" size="icon" onClick={onZoomIn} title="Zoom in">
          <ZoomIn className="h-4 w-4" />
        </Button>

        <Button variant="ghost" size="icon" onClick={onZoomReset} title="Fit to view">
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>

      {/* View toggles */}
      <div className="flex items-center gap-1 border-r pr-2 mr-2">
        <Button
          variant={showGrid ? 'secondary' : 'ghost'}
          size="icon"
          onClick={onToggleGrid}
          title={showGrid ? 'Hide grid' : 'Show grid'}
        >
          <Grid3X3 className="h-4 w-4" />
        </Button>

        <Button
          variant={showNetLabels ? 'secondary' : 'ghost'}
          size="icon"
          onClick={onToggleNetLabels}
          title={showNetLabels ? 'Hide net labels' : 'Show net labels'}
        >
          {showNetLabels ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
        </Button>

        <Button
          variant={showValues ? 'secondary' : 'ghost'}
          size="sm"
          onClick={onToggleValues}
          title={showValues ? 'Hide values' : 'Show values'}
          className="text-xs"
        >
          10k
        </Button>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Settings */}
      <Button variant="ghost" size="icon" onClick={onOpenSettings} title="Settings">
        <Settings className="h-4 w-4" />
      </Button>
    </div>
  )
}
