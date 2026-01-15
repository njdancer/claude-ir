import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { X, Filter, Layers, Network, GitBranch } from 'lucide-react'
import type { FilterMode, FilterConfig } from '@/state'

interface FilterPanelProps {
  filter: FilterConfig
  netNames: string[]
  componentRefs: string[]
  onFilterChange: (filter: Partial<FilterConfig>) => void
  onResetFilter: () => void
}

/**
 * Filter panel for controlling schematic view
 */
export function FilterPanel({
  filter,
  netNames,
  componentRefs,
  onFilterChange,
  onResetFilter,
}: FilterPanelProps) {
  const [searchTerm, setSearchTerm] = useState('')

  // Filter nets/components by search term
  const filteredNets = netNames.filter((n) =>
    n.toLowerCase().includes(searchTerm.toLowerCase())
  )
  const filteredComponents = componentRefs.filter((c) =>
    c.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleModeChange = (mode: FilterMode) => {
    onFilterChange({ mode })
  }

  const handleNetToggle = (net: string) => {
    const newNets = filter.nets.includes(net)
      ? filter.nets.filter((n) => n !== net)
      : [...filter.nets, net]
    onFilterChange({ nets: newNets })
  }

  const handleComponentToggle = (ref: string) => {
    const newComponents = filter.components.includes(ref)
      ? filter.components.filter((c) => c !== ref)
      : [...filter.components, ref]
    onFilterChange({ components: newComponents })
  }

  const handleNeighborhoodCenterChange = (center: string) => {
    onFilterChange({ neighborhoodCenter: center || null })
  }

  const handleDepthChange = (depth: string) => {
    onFilterChange({ neighborhoodDepth: parseInt(depth, 10) })
  }

  const isFiltered = filter.mode !== 'all'

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <Filter className="h-4 w-4" />
          Filters
        </h3>
        {isFiltered && (
          <Button variant="ghost" size="sm" onClick={onResetFilter}>
            <X className="h-3 w-3 mr-1" />
            Clear
          </Button>
        )}
      </div>

      {/* Filter mode selector */}
      <div className="space-y-2">
        <Label>Filter Mode</Label>
        <Select value={filter.mode} onValueChange={(v) => handleModeChange(v as FilterMode)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4" />
                Show All
              </div>
            </SelectItem>
            <SelectItem value="net">
              <div className="flex items-center gap-2">
                <Network className="h-4 w-4" />
                Filter by Net
              </div>
            </SelectItem>
            <SelectItem value="component">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                Filter by Component
              </div>
            </SelectItem>
            <SelectItem value="neighborhood">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                Neighborhood View
              </div>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Search */}
      {filter.mode !== 'all' && (
        <div className="space-y-2">
          <Label>Search</Label>
          <Input
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      )}

      {/* Net filter */}
      {filter.mode === 'net' && (
        <div className="space-y-2">
          <Label>Selected Nets</Label>
          <div className="flex flex-wrap gap-1">
            {filter.nets.map((net) => (
              <Badge key={net} variant="secondary" className="cursor-pointer" onClick={() => handleNetToggle(net)}>
                {net}
                <X className="h-3 w-3 ml-1" />
              </Badge>
            ))}
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1 border rounded p-2">
            {filteredNets.map((net) => (
              <button
                key={net}
                className={`w-full text-left px-2 py-1 rounded text-sm hover:bg-slate-100 ${
                  filter.nets.includes(net) ? 'bg-slate-100 font-medium' : ''
                }`}
                onClick={() => handleNetToggle(net)}
              >
                {net}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Component filter */}
      {filter.mode === 'component' && (
        <div className="space-y-2">
          <Label>Selected Components</Label>
          <div className="flex flex-wrap gap-1">
            {filter.components.map((ref) => (
              <Badge key={ref} variant="secondary" className="cursor-pointer" onClick={() => handleComponentToggle(ref)}>
                {ref}
                <X className="h-3 w-3 ml-1" />
              </Badge>
            ))}
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1 border rounded p-2">
            {filteredComponents.map((ref) => (
              <button
                key={ref}
                className={`w-full text-left px-2 py-1 rounded text-sm hover:bg-slate-100 ${
                  filter.components.includes(ref) ? 'bg-slate-100 font-medium' : ''
                }`}
                onClick={() => handleComponentToggle(ref)}
              >
                {ref}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Neighborhood filter */}
      {filter.mode === 'neighborhood' && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Center Component</Label>
            <Select
              value={filter.neighborhoodCenter ?? ''}
              onValueChange={handleNeighborhoodCenterChange}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select component..." />
              </SelectTrigger>
              <SelectContent>
                {componentRefs.map((ref) => (
                  <SelectItem key={ref} value={ref}>
                    {ref}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Depth: {filter.neighborhoodDepth}</Label>
            <Select
              value={filter.neighborhoodDepth.toString()}
              onValueChange={handleDepthChange}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4, 5].map((d) => (
                  <SelectItem key={d} value={d.toString()}>
                    {d} {d === 1 ? 'hop' : 'hops'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}
    </div>
  )
}
