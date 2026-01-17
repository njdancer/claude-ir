import { useReducer, useMemo, type ReactNode } from 'react'
import type { FilterConfig, ViewportTransform } from './types'
import type { CircuitAST } from '@/parser'
import type { CircuitGraph } from '@/graph'
import type { ValidationResult } from '@/validation'
import type { LayoutResult } from '@/layout'
import type { SymbolStandard } from '@/symbols'
import { AppContext } from './AppContext'
import { appReducer, initialAppState } from './reducers'

/**
 * App state provider
 */
export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialAppState)

  // Memoized action creators
  const actions = useMemo(
    () => ({
      // Project actions
      loadProject: (filename: string, content: string) =>
        dispatch({ type: 'project/load', payload: { filename, content } }),
      clearProject: () => dispatch({ type: 'project/clear' }),
      setAST: (ast: CircuitAST) => dispatch({ type: 'project/setAST', payload: ast }),
      setGraph: (graph: CircuitGraph) => dispatch({ type: 'project/setGraph', payload: graph }),
      setValidation: (validation: ValidationResult) =>
        dispatch({ type: 'project/setValidation', payload: validation }),
      setLayout: (layout: LayoutResult) => dispatch({ type: 'project/setLayout', payload: layout }),
      setError: (error: string) => dispatch({ type: 'project/setError', payload: error }),

      // View actions
      setFilter: (filter: Partial<FilterConfig>) =>
        dispatch({ type: 'view/setFilter', payload: filter }),
      resetFilter: () => dispatch({ type: 'view/resetFilter' }),
      setViewport: (viewport: Partial<ViewportTransform>) =>
        dispatch({ type: 'view/setViewport', payload: viewport }),
      resetViewport: () => dispatch({ type: 'view/resetViewport' }),
      selectNodes: (nodeIds: string[]) => dispatch({ type: 'view/selectNodes', payload: nodeIds }),
      toggleNodeSelection: (nodeId: string) =>
        dispatch({ type: 'view/toggleNodeSelection', payload: nodeId }),
      clearSelection: () => dispatch({ type: 'view/clearSelection' }),
      setHoveredNode: (nodeId: string | null) =>
        dispatch({ type: 'view/setHoveredNode', payload: nodeId }),
      toggleShowValidation: () => dispatch({ type: 'view/toggleShowValidation' }),
      toggleShowNetLabels: () => dispatch({ type: 'view/toggleShowNetLabels' }),
      toggleShowValues: () => dispatch({ type: 'view/toggleShowValues' }),

      // UI actions
      toggleSidebar: () => dispatch({ type: 'ui/toggleSidebar' }),
      toggleFilePanel: () => dispatch({ type: 'ui/toggleFilePanel' }),
      toggleValidationPanel: () => dispatch({ type: 'ui/toggleValidationPanel' }),
      openSettingsDialog: () => dispatch({ type: 'ui/openSettingsDialog' }),
      closeSettingsDialog: () => dispatch({ type: 'ui/closeSettingsDialog' }),
      openHelpDialog: () => dispatch({ type: 'ui/openHelpDialog' }),
      closeHelpDialog: () => dispatch({ type: 'ui/closeHelpDialog' }),

      // Preferences actions
      setSymbolStandard: (standard: SymbolStandard) =>
        dispatch({ type: 'preferences/setSymbolStandard', payload: standard }),
      setTheme: (theme: 'light' | 'dark' | 'system') =>
        dispatch({ type: 'preferences/setTheme', payload: theme }),
      toggleShowGrid: () => dispatch({ type: 'preferences/toggleShowGrid' }),
      toggleSnapToGrid: () => dispatch({ type: 'preferences/toggleSnapToGrid' }),
      setGridSize: (size: number) => dispatch({ type: 'preferences/setGridSize', payload: size }),
    }),
    [dispatch]
  )

  const value = useMemo(() => ({ state, dispatch, actions }), [state, dispatch, actions])

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
