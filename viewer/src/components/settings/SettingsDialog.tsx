import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import type { SymbolStandard } from '@/symbols'

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  symbolStandard: SymbolStandard
  theme: 'light' | 'dark' | 'system'
  showGrid: boolean
  snapToGrid: boolean
  gridSize: number
  onSymbolStandardChange: (standard: SymbolStandard) => void
  onThemeChange: (theme: 'light' | 'dark' | 'system') => void
  onShowGridChange: () => void
  onSnapToGridChange: () => void
  onGridSizeChange: (size: number) => void
}

/**
 * Settings dialog for user preferences
 */
export function SettingsDialog({
  open,
  onOpenChange,
  symbolStandard,
  theme,
  showGrid,
  snapToGrid,
  gridSize,
  onSymbolStandardChange,
  onThemeChange,
  onShowGridChange,
  onSnapToGridChange,
  onGridSizeChange,
}: SettingsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Configure your schematic viewer preferences</DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Symbol Standard */}
          <div className="space-y-2">
            <Label htmlFor="symbol-standard">Symbol Standard</Label>
            <Select
              value={symbolStandard}
              onValueChange={(v) => onSymbolStandardChange(v as SymbolStandard)}
            >
              <SelectTrigger id="symbol-standard">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ieee">IEEE (US)</SelectItem>
                <SelectItem value="iec">IEC (European)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-slate-500">
              {symbolStandard === 'ieee'
                ? 'Uses rectangular resistors and other US-style symbols'
                : 'Uses zigzag resistors and other European-style symbols'}
            </p>
          </div>

          {/* Theme */}
          <div className="space-y-2">
            <Label htmlFor="theme">Theme</Label>
            <Select
              value={theme}
              onValueChange={(v) => onThemeChange(v as 'light' | 'dark' | 'system')}
            >
              <SelectTrigger id="theme">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Grid Settings */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium">Grid Settings</h4>

            <div className="flex items-center justify-between">
              <Label htmlFor="show-grid">Show Grid</Label>
              <Switch id="show-grid" checked={showGrid} onCheckedChange={onShowGridChange} />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="snap-grid">Snap to Grid</Label>
              <Switch id="snap-grid" checked={snapToGrid} onCheckedChange={onSnapToGridChange} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="grid-size">Grid Size</Label>
              <Select
                value={gridSize.toString()}
                onValueChange={(v) => onGridSizeChange(parseInt(v, 10))}
              >
                <SelectTrigger id="grid-size">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5">5px</SelectItem>
                  <SelectItem value="10">10px</SelectItem>
                  <SelectItem value="20">20px</SelectItem>
                  <SelectItem value="25">25px</SelectItem>
                  <SelectItem value="50">50px</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
