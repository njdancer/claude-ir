import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Filter, AlertTriangle, FileText, X } from 'lucide-react'
import { FilterPanel } from './FilterPanel'
import { ValidationPanel } from '../validation/ValidationPanel'
import type { FilterConfig } from '@/state'
import type { ValidationResult } from '@/validation'

interface SidebarProps {
  filter: FilterConfig
  netNames: string[]
  componentRefs: string[]
  validation: ValidationResult | null
  filename: string | null
  onFilterChange: (filter: Partial<FilterConfig>) => void
  onResetFilter: () => void
  onClose?: () => void
}

/**
 * Main sidebar component containing filter and validation panels
 */
export function Sidebar({
  filter,
  netNames,
  componentRefs,
  validation,
  filename,
  onFilterChange,
  onResetFilter,
  onClose,
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState('filter')

  const errorCount = validation?.counts.error ?? 0
  const warningCount = validation?.counts.warning ?? 0
  const hasIssues = errorCount > 0 || warningCount > 0

  return (
    <div className="flex h-full w-80 flex-col border-r bg-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-slate-500" />
          <span className="text-sm font-medium truncate max-w-[180px]">
            {filename || 'No file loaded'}
          </span>
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start rounded-none border-b bg-transparent px-4">
          <TabsTrigger
            value="filter"
            className="gap-2 data-[state=active]:bg-transparent data-[state=active]:shadow-none"
          >
            <Filter className="h-4 w-4" />
            Filter
          </TabsTrigger>
          <TabsTrigger
            value="validation"
            className="gap-2 data-[state=active]:bg-transparent data-[state=active]:shadow-none"
          >
            <AlertTriangle className="h-4 w-4" />
            Validation
            {hasIssues && (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">
                {errorCount + warningCount}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="filter" className="flex-1 m-0 overflow-auto">
          <FilterPanel
            filter={filter}
            netNames={netNames}
            componentRefs={componentRefs}
            onFilterChange={onFilterChange}
            onResetFilter={onResetFilter}
          />
        </TabsContent>

        <TabsContent value="validation" className="flex-1 m-0 overflow-auto">
          <ValidationPanel validation={validation} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
