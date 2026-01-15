import type { AppState } from './types'
import type { CircuitGraph, ComponentGraphNode, SubcircuitGraphNode } from '@/graph'
import { filterByNets, filterByComponents, filterByNeighborhood } from '@/graph'

/**
 * Get the filtered graph based on current filter settings
 */
export function selectFilteredGraph(state: AppState): CircuitGraph | null {
  const { graph } = state.project
  const { filter } = state.view

  if (!graph) return null

  switch (filter.mode) {
    case 'all':
      return graph

    case 'net':
      if (filter.nets.length === 0) return graph
      return filterByNets(graph, filter.nets).graph

    case 'component':
      if (filter.components.length === 0) return graph
      return filterByComponents(graph, filter.components).graph

    case 'neighborhood':
      if (!filter.neighborhoodCenter) return graph
      return filterByNeighborhood(graph, filter.neighborhoodCenter, filter.neighborhoodDepth).graph

    default:
      return graph
  }
}

/**
 * Get all net names from the graph
 */
export function selectNetNames(state: AppState): string[] {
  const { graph } = state.project
  if (!graph) return []

  const nets: string[] = []
  for (const node of graph.nodes.values()) {
    if (node.type === 'net') {
      nets.push(node.label)
    }
  }
  return nets.sort()
}

/**
 * Get all component references from the graph
 */
export function selectComponentRefs(state: AppState): string[] {
  const { graph } = state.project
  if (!graph) return []

  const refs: string[] = []
  for (const node of graph.nodes.values()) {
    if (node.type === 'component') {
      refs.push((node as ComponentGraphNode).ref)
    } else if (node.type === 'subcircuit') {
      refs.push((node as SubcircuitGraphNode).ref)
    }
  }
  return refs.sort()
}

/**
 * Get validation error count
 */
export function selectErrorCount(state: AppState): number {
  return state.project.validation?.counts.error ?? 0
}

/**
 * Get validation warning count
 */
export function selectWarningCount(state: AppState): number {
  return state.project.validation?.counts.warning ?? 0
}

/**
 * Check if project has any validation issues
 */
export function selectHasValidationIssues(state: AppState): boolean {
  const counts = state.project.validation?.counts
  if (!counts) return false
  return counts.error > 0 || counts.warning > 0
}

/**
 * Get current theme (resolved from 'system' to actual theme)
 */
export function selectResolvedTheme(state: AppState): 'light' | 'dark' {
  if (state.preferences.theme === 'system') {
    // Check system preference
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'light'
  }
  return state.preferences.theme
}

/**
 * Check if any node is selected
 */
export function selectHasSelection(state: AppState): boolean {
  return state.view.selection.selectedNodes.size > 0
}

/**
 * Get selected node count
 */
export function selectSelectionCount(state: AppState): number {
  return state.view.selection.selectedNodes.size
}

/**
 * Check if a specific node is selected
 */
export function selectIsNodeSelected(state: AppState, nodeId: string): boolean {
  return state.view.selection.selectedNodes.has(nodeId)
}

/**
 * Check if a specific node is hovered
 */
export function selectIsNodeHovered(state: AppState, nodeId: string): boolean {
  return state.view.selection.hoveredNode === nodeId
}

/**
 * Get the zoom percentage
 */
export function selectZoomPercentage(state: AppState): number {
  return Math.round(state.view.viewport.zoom * 100)
}

/**
 * Check if project is loaded
 */
export function selectIsProjectLoaded(state: AppState): boolean {
  return state.project.graph !== null
}

/**
 * Check if project is loading
 */
export function selectIsProjectLoading(state: AppState): boolean {
  return state.project.loading
}

/**
 * Get project error if any
 */
export function selectProjectError(state: AppState): string | null {
  return state.project.error
}
