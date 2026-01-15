import { useContext } from 'react'
import { AppContext, type AppContextValue } from './AppContext'

/**
 * Hook to access app state and actions
 */
export function useAppState(): AppContextValue {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useAppState must be used within an AppStateProvider')
  }
  return context
}

/**
 * Hook to access just the project state
 */
export function useProjectState() {
  const { state } = useAppState()
  return state.project
}

/**
 * Hook to access just the view state
 */
export function useViewState() {
  const { state } = useAppState()
  return state.view
}

/**
 * Hook to access just the UI state
 */
export function useUIState() {
  const { state } = useAppState()
  return state.ui
}

/**
 * Hook to access just the preferences state
 */
export function usePreferencesState() {
  const { state } = useAppState()
  return state.preferences
}

/**
 * Hook to access filter configuration
 */
export function useFilter() {
  const { state, actions } = useAppState()
  return {
    filter: state.view.filter,
    setFilter: actions.setFilter,
    resetFilter: actions.resetFilter,
  }
}

/**
 * Hook to access viewport state
 */
export function useViewport() {
  const { state, actions } = useAppState()
  return {
    viewport: state.view.viewport,
    setViewport: actions.setViewport,
    resetViewport: actions.resetViewport,
  }
}

/**
 * Hook to access selection state
 */
export function useSelection() {
  const { state, actions } = useAppState()
  return {
    selection: state.view.selection,
    selectedNodes: state.view.selection.selectedNodes,
    hoveredNode: state.view.selection.hoveredNode,
    selectNodes: actions.selectNodes,
    toggleNodeSelection: actions.toggleNodeSelection,
    clearSelection: actions.clearSelection,
    setHoveredNode: actions.setHoveredNode,
  }
}
