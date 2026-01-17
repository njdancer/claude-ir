import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
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
    <TooltipProvider delayDuration={300}>
      <div className="flex items-center gap-2 p-2 border-b bg-white">
        {/* Zoom controls */}
        <div className="flex items-center gap-1 border-r pr-2 mr-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={onZoomOut} aria-label="Zoom out">
                <ZoomOut className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Zoom out (scroll down)</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={onZoomReset}
                className="min-w-[60px] font-mono text-sm"
              >
                {zoomPercent}%
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Click to reset zoom to 100%</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={onZoomIn} aria-label="Zoom in">
                <ZoomIn className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Zoom in (scroll up)</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={onZoomReset} aria-label="Fit to view">
                <Maximize2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Fit schematic to view</p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* View toggles */}
        <div className="flex items-center gap-1 border-r pr-2 mr-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={showGrid ? 'secondary' : 'ghost'}
                size="icon"
                onClick={onToggleGrid}
                aria-label={showGrid ? 'Hide grid' : 'Show grid'}
              >
                <Grid3X3 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{showGrid ? 'Hide background grid' : 'Show background grid'}</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={showNetLabels ? 'secondary' : 'ghost'}
                size="icon"
                onClick={onToggleNetLabels}
                aria-label={showNetLabels ? 'Hide labels' : 'Show labels'}
              >
                {showNetLabels ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{showNetLabels ? 'Hide net labels' : 'Show net labels on wires'}</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={showValues ? 'secondary' : 'ghost'}
                size="sm"
                onClick={onToggleValues}
                className="text-xs"
              >
                10k
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{showValues ? 'Hide component values' : 'Show component values (10k, 100nF, etc.)'}</p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Settings */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" onClick={onOpenSettings} aria-label="Settings">
              <Settings className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Settings (symbol style, theme, grid)</p>
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  )
}
