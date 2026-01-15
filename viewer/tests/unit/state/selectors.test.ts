import { describe, it, expect } from 'vitest'
import { parse } from '@/parser'
import { buildGraph } from '@/graph'
import { validate } from '@/validation'
import { initialAppState } from '@/state/reducers'
import {
  selectFilteredGraph,
  selectNetNames,
  selectComponentRefs,
  selectErrorCount,
  selectWarningCount,
  selectHasValidationIssues,
  selectHasSelection,
  selectSelectionCount,
  selectIsNodeSelected,
  selectIsNodeHovered,
  selectZoomPercentage,
  selectIsProjectLoaded,
  selectIsProjectLoading,
} from '@/state/selectors'
import type { AppState } from '@/state/types'

describe('state selectors', () => {
  // Helper to create state with a loaded project
  function createStateWithProject(): AppState {
    const ast = parse(
      `[VCC]: net
[GND]: net
[U1]: esp32
[R1]: resistor(10k)
[U1.VCC --- VCC]
[U1.GND --- GND]`,
      'test.circuit.md'
    )
    const graph = buildGraph(ast)
    const validation = validate(ast, graph)

    return {
      ...initialAppState,
      project: {
        ...initialAppState.project,
        filename: 'test.circuit.md',
        ast,
        graph,
        validation,
      },
    }
  }

  describe('selectFilteredGraph', () => {
    it('should return full graph when filter mode is all', () => {
      const state = createStateWithProject()
      const filtered = selectFilteredGraph(state)

      expect(filtered).toBe(state.project.graph)
    })

    it('should filter by nets when mode is net', () => {
      let state = createStateWithProject()
      state = {
        ...state,
        view: {
          ...state.view,
          filter: {
            ...state.view.filter,
            mode: 'net',
            nets: ['VCC'],
          },
        },
      }

      const filtered = selectFilteredGraph(state)
      expect(filtered).toBeDefined()
      expect(filtered!.nodes.size).toBeLessThan(state.project.graph!.nodes.size)
    })

    it('should return null when no graph is loaded', () => {
      const filtered = selectFilteredGraph(initialAppState)
      expect(filtered).toBeNull()
    })
  })

  describe('selectNetNames', () => {
    it('should return sorted net names', () => {
      const state = createStateWithProject()
      const nets = selectNetNames(state)

      expect(nets).toContain('VCC')
      expect(nets).toContain('GND')
      expect(nets).toEqual([...nets].sort())
    })

    it('should return empty array when no graph', () => {
      const nets = selectNetNames(initialAppState)
      expect(nets).toEqual([])
    })
  })

  describe('selectComponentRefs', () => {
    it('should return sorted component references', () => {
      const state = createStateWithProject()
      const refs = selectComponentRefs(state)

      expect(refs).toContain('U1')
      expect(refs).toContain('R1')
    })

    it('should return empty array when no graph', () => {
      const refs = selectComponentRefs(initialAppState)
      expect(refs).toEqual([])
    })
  })

  describe('validation selectors', () => {
    it('selectErrorCount should return error count', () => {
      const state = createStateWithProject()
      const count = selectErrorCount(state)

      expect(typeof count).toBe('number')
    })

    it('selectWarningCount should return warning count', () => {
      const state = createStateWithProject()
      const count = selectWarningCount(state)

      expect(typeof count).toBe('number')
    })

    it('selectHasValidationIssues should indicate presence of issues', () => {
      const state = createStateWithProject()
      // This test circuit has connectivity warnings (single connection nets)
      expect(selectHasValidationIssues(state)).toBe(true)
    })
  })

  describe('selection selectors', () => {
    it('selectHasSelection should return false when nothing selected', () => {
      expect(selectHasSelection(initialAppState)).toBe(false)
    })

    it('selectHasSelection should return true when nodes selected', () => {
      const state = {
        ...initialAppState,
        view: {
          ...initialAppState.view,
          selection: {
            ...initialAppState.view.selection,
            selectedNodes: new Set(['node1']),
          },
        },
      }
      expect(selectHasSelection(state)).toBe(true)
    })

    it('selectSelectionCount should return count', () => {
      const state = {
        ...initialAppState,
        view: {
          ...initialAppState.view,
          selection: {
            ...initialAppState.view.selection,
            selectedNodes: new Set(['node1', 'node2']),
          },
        },
      }
      expect(selectSelectionCount(state)).toBe(2)
    })

    it('selectIsNodeSelected should check specific node', () => {
      const state = {
        ...initialAppState,
        view: {
          ...initialAppState.view,
          selection: {
            ...initialAppState.view.selection,
            selectedNodes: new Set(['node1']),
          },
        },
      }
      expect(selectIsNodeSelected(state, 'node1')).toBe(true)
      expect(selectIsNodeSelected(state, 'node2')).toBe(false)
    })

    it('selectIsNodeHovered should check hovered node', () => {
      const state = {
        ...initialAppState,
        view: {
          ...initialAppState.view,
          selection: {
            ...initialAppState.view.selection,
            hoveredNode: 'node1',
          },
        },
      }
      expect(selectIsNodeHovered(state, 'node1')).toBe(true)
      expect(selectIsNodeHovered(state, 'node2')).toBe(false)
    })
  })

  describe('viewport selectors', () => {
    it('selectZoomPercentage should return zoom as percentage', () => {
      const state = {
        ...initialAppState,
        view: {
          ...initialAppState.view,
          viewport: {
            ...initialAppState.view.viewport,
            zoom: 1.5,
          },
        },
      }
      expect(selectZoomPercentage(state)).toBe(150)
    })
  })

  describe('project state selectors', () => {
    it('selectIsProjectLoaded should return true when graph exists', () => {
      const state = createStateWithProject()
      expect(selectIsProjectLoaded(state)).toBe(true)
    })

    it('selectIsProjectLoaded should return false when no graph', () => {
      expect(selectIsProjectLoaded(initialAppState)).toBe(false)
    })

    it('selectIsProjectLoading should reflect loading state', () => {
      const loadingState = {
        ...initialAppState,
        project: {
          ...initialAppState.project,
          loading: true,
        },
      }
      expect(selectIsProjectLoading(loadingState)).toBe(true)
      expect(selectIsProjectLoading(initialAppState)).toBe(false)
    })
  })
})
