import { createContext } from 'react'
import type { AppState, AppAction, FilterConfig, ViewportTransform } from './types'
import type { SymbolStandard } from '@/symbols'

/**
 * Context value with state and actions
 */
export interface AppContextValue {
  state: AppState
  dispatch: React.Dispatch<AppAction>
  // Convenience action creators
  actions: {
    // Project actions
    loadProject: (filename: string, content: string) => void
    clearProject: () => void
    // View actions
    setFilter: (filter: Partial<FilterConfig>) => void
    resetFilter: () => void
    setViewport: (viewport: Partial<ViewportTransform>) => void
    resetViewport: () => void
    selectNodes: (nodeIds: string[]) => void
    toggleNodeSelection: (nodeId: string) => void
    clearSelection: () => void
    setHoveredNode: (nodeId: string | null) => void
    toggleShowValidation: () => void
    toggleShowNetLabels: () => void
    toggleShowValues: () => void
    // UI actions
    toggleSidebar: () => void
    toggleFilePanel: () => void
    toggleValidationPanel: () => void
    openSettingsDialog: () => void
    closeSettingsDialog: () => void
    openHelpDialog: () => void
    closeHelpDialog: () => void
    // Preferences actions
    setSymbolStandard: (standard: SymbolStandard) => void
    setTheme: (theme: 'light' | 'dark' | 'system') => void
    toggleShowGrid: () => void
    toggleSnapToGrid: () => void
    setGridSize: (size: number) => void
  }
}

export const AppContext = createContext<AppContextValue | null>(null)
