import { describe, it, expect } from 'vitest'
import { appReducer, initialAppState, initialFilter } from '@/state/reducers'
import type { AppAction } from '@/state/types'

describe('state reducers', () => {
  describe('project reducer', () => {
    it('should handle project/load', () => {
      const action: AppAction = {
        type: 'project/load',
        payload: { filename: 'test.circuit.md', content: '[VCC]: net' },
      }
      const state = appReducer(initialAppState, action)

      expect(state.project.filename).toBe('test.circuit.md')
      expect(state.project.sourceContent).toBe('[VCC]: net')
      expect(state.project.loading).toBe(true)
      expect(state.project.error).toBeNull()
    })

    it('should handle project/setError', () => {
      const action: AppAction = {
        type: 'project/setError',
        payload: 'Parse error',
      }
      const state = appReducer(initialAppState, action)

      expect(state.project.error).toBe('Parse error')
      expect(state.project.loading).toBe(false)
    })

    it('should handle project/clear', () => {
      // First load a project
      let state = appReducer(initialAppState, {
        type: 'project/load',
        payload: { filename: 'test.circuit.md', content: '[VCC]: net' },
      })

      // Then clear it
      state = appReducer(state, { type: 'project/clear' })

      expect(state.project.filename).toBeNull()
      expect(state.project.sourceContent).toBeNull()
      expect(state.project.loading).toBe(false)
    })
  })

  describe('view reducer', () => {
    it('should handle view/setFilter', () => {
      const action: AppAction = {
        type: 'view/setFilter',
        payload: { mode: 'net', nets: ['VCC', 'GND'] },
      }
      const state = appReducer(initialAppState, action)

      expect(state.view.filter.mode).toBe('net')
      expect(state.view.filter.nets).toEqual(['VCC', 'GND'])
    })

    it('should handle view/resetFilter', () => {
      // First set a filter
      let state = appReducer(initialAppState, {
        type: 'view/setFilter',
        payload: { mode: 'net', nets: ['VCC'] },
      })

      // Then reset it
      state = appReducer(state, { type: 'view/resetFilter' })

      expect(state.view.filter).toEqual(initialFilter)
    })

    it('should handle view/setViewport', () => {
      const action: AppAction = {
        type: 'view/setViewport',
        payload: { panX: 100, panY: 50, zoom: 1.5 },
      }
      const state = appReducer(initialAppState, action)

      expect(state.view.viewport.panX).toBe(100)
      expect(state.view.viewport.panY).toBe(50)
      expect(state.view.viewport.zoom).toBe(1.5)
    })

    it('should handle view/selectNodes', () => {
      const action: AppAction = {
        type: 'view/selectNodes',
        payload: ['node1', 'node2'],
      }
      const state = appReducer(initialAppState, action)

      expect(state.view.selection.selectedNodes.has('node1')).toBe(true)
      expect(state.view.selection.selectedNodes.has('node2')).toBe(true)
      expect(state.view.selection.selectedNodes.size).toBe(2)
    })

    it('should handle view/toggleNodeSelection', () => {
      // Select a node
      let state = appReducer(initialAppState, {
        type: 'view/toggleNodeSelection',
        payload: 'node1',
      })
      expect(state.view.selection.selectedNodes.has('node1')).toBe(true)

      // Toggle again to deselect
      state = appReducer(state, {
        type: 'view/toggleNodeSelection',
        payload: 'node1',
      })
      expect(state.view.selection.selectedNodes.has('node1')).toBe(false)
    })

    it('should handle view/clearSelection', () => {
      // Select some nodes
      let state = appReducer(initialAppState, {
        type: 'view/selectNodes',
        payload: ['node1', 'node2'],
      })

      // Clear selection
      state = appReducer(state, { type: 'view/clearSelection' })

      expect(state.view.selection.selectedNodes.size).toBe(0)
    })

    it('should handle view/setHoveredNode', () => {
      const action: AppAction = {
        type: 'view/setHoveredNode',
        payload: 'node1',
      }
      const state = appReducer(initialAppState, action)

      expect(state.view.selection.hoveredNode).toBe('node1')
    })

    it('should handle view/toggleShowValidation', () => {
      const initialValue = initialAppState.view.showValidation
      const state = appReducer(initialAppState, { type: 'view/toggleShowValidation' })

      expect(state.view.showValidation).toBe(!initialValue)
    })
  })

  describe('ui reducer', () => {
    it('should handle ui/toggleSidebar', () => {
      const initialValue = initialAppState.ui.sidebarVisible
      const state = appReducer(initialAppState, { type: 'ui/toggleSidebar' })

      expect(state.ui.sidebarVisible).toBe(!initialValue)
    })

    it('should handle ui/openSettingsDialog and ui/closeSettingsDialog', () => {
      let state = appReducer(initialAppState, { type: 'ui/openSettingsDialog' })
      expect(state.ui.settingsDialogOpen).toBe(true)

      state = appReducer(state, { type: 'ui/closeSettingsDialog' })
      expect(state.ui.settingsDialogOpen).toBe(false)
    })
  })

  describe('preferences reducer', () => {
    it('should handle preferences/setSymbolStandard', () => {
      const action: AppAction = {
        type: 'preferences/setSymbolStandard',
        payload: 'iec',
      }
      const state = appReducer(initialAppState, action)

      expect(state.preferences.symbolStandard).toBe('iec')
    })

    it('should handle preferences/setTheme', () => {
      const action: AppAction = {
        type: 'preferences/setTheme',
        payload: 'dark',
      }
      const state = appReducer(initialAppState, action)

      expect(state.preferences.theme).toBe('dark')
    })

    it('should handle preferences/toggleShowGrid', () => {
      const initialValue = initialAppState.preferences.showGrid
      const state = appReducer(initialAppState, { type: 'preferences/toggleShowGrid' })

      expect(state.preferences.showGrid).toBe(!initialValue)
    })

    it('should handle preferences/setGridSize', () => {
      const action: AppAction = {
        type: 'preferences/setGridSize',
        payload: 20,
      }
      const state = appReducer(initialAppState, action)

      expect(state.preferences.gridSize).toBe(20)
    })
  })
})
