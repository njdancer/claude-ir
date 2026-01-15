import type {
  AppState,
  AppAction,
  ProjectState,
  ViewState,
  UIState,
  PreferencesState,
  FilterConfig,
} from './types'

/**
 * Initial filter configuration
 */
export const initialFilter: FilterConfig = {
  mode: 'all',
  nets: [],
  components: [],
  neighborhoodCenter: null,
  neighborhoodDepth: 2,
}

/**
 * Initial project state
 */
export const initialProjectState: ProjectState = {
  filename: null,
  sourceContent: null,
  ast: null,
  graph: null,
  validation: null,
  layout: null,
  loading: false,
  error: null,
}

/**
 * Initial view state
 */
export const initialViewState: ViewState = {
  filter: initialFilter,
  viewport: {
    panX: 0,
    panY: 0,
    zoom: 1,
  },
  selection: {
    selectedNodes: new Set(),
    hoveredNode: null,
    selectedEdges: new Set(),
  },
  showValidation: true,
  showNetLabels: true,
  showValues: true,
}

/**
 * Initial UI state
 */
export const initialUIState: UIState = {
  sidebarVisible: true,
  filePanelVisible: true,
  validationPanelVisible: true,
  settingsDialogOpen: false,
  helpDialogOpen: false,
}

/**
 * Initial preferences state
 */
export const initialPreferencesState: PreferencesState = {
  symbolStandard: 'ieee',
  theme: 'system',
  showGrid: true,
  snapToGrid: true,
  gridSize: 10,
}

/**
 * Initial complete app state
 */
export const initialAppState: AppState = {
  project: initialProjectState,
  view: initialViewState,
  ui: initialUIState,
  preferences: initialPreferencesState,
}

/**
 * Project state reducer
 */
function projectReducer(state: ProjectState, action: AppAction): ProjectState {
  switch (action.type) {
    case 'project/load':
      return {
        ...state,
        filename: action.payload.filename,
        sourceContent: action.payload.content,
        loading: true,
        error: null,
      }
    case 'project/setAST':
      return { ...state, ast: action.payload }
    case 'project/setGraph':
      return { ...state, graph: action.payload }
    case 'project/setValidation':
      return { ...state, validation: action.payload }
    case 'project/setLayout':
      return { ...state, layout: action.payload, loading: false }
    case 'project/setError':
      return { ...state, error: action.payload, loading: false }
    case 'project/clear':
      return initialProjectState
    default:
      return state
  }
}

/**
 * View state reducer
 */
function viewReducer(state: ViewState, action: AppAction): ViewState {
  switch (action.type) {
    case 'view/setFilter':
      return {
        ...state,
        filter: { ...state.filter, ...action.payload },
      }
    case 'view/resetFilter':
      return { ...state, filter: initialFilter }
    case 'view/setViewport':
      return {
        ...state,
        viewport: { ...state.viewport, ...action.payload },
      }
    case 'view/resetViewport':
      return {
        ...state,
        viewport: { panX: 0, panY: 0, zoom: 1 },
      }
    case 'view/selectNodes': {
      const newSelection = new Set(action.payload)
      return {
        ...state,
        selection: { ...state.selection, selectedNodes: newSelection },
      }
    }
    case 'view/toggleNodeSelection': {
      const newSelection = new Set(state.selection.selectedNodes)
      if (newSelection.has(action.payload)) {
        newSelection.delete(action.payload)
      } else {
        newSelection.add(action.payload)
      }
      return {
        ...state,
        selection: { ...state.selection, selectedNodes: newSelection },
      }
    }
    case 'view/clearSelection':
      return {
        ...state,
        selection: {
          ...state.selection,
          selectedNodes: new Set(),
          selectedEdges: new Set(),
        },
      }
    case 'view/setHoveredNode':
      return {
        ...state,
        selection: { ...state.selection, hoveredNode: action.payload },
      }
    case 'view/toggleShowValidation':
      return { ...state, showValidation: !state.showValidation }
    case 'view/toggleShowNetLabels':
      return { ...state, showNetLabels: !state.showNetLabels }
    case 'view/toggleShowValues':
      return { ...state, showValues: !state.showValues }
    default:
      return state
  }
}

/**
 * UI state reducer
 */
function uiReducer(state: UIState, action: AppAction): UIState {
  switch (action.type) {
    case 'ui/toggleSidebar':
      return { ...state, sidebarVisible: !state.sidebarVisible }
    case 'ui/toggleFilePanel':
      return { ...state, filePanelVisible: !state.filePanelVisible }
    case 'ui/toggleValidationPanel':
      return { ...state, validationPanelVisible: !state.validationPanelVisible }
    case 'ui/openSettingsDialog':
      return { ...state, settingsDialogOpen: true }
    case 'ui/closeSettingsDialog':
      return { ...state, settingsDialogOpen: false }
    case 'ui/openHelpDialog':
      return { ...state, helpDialogOpen: true }
    case 'ui/closeHelpDialog':
      return { ...state, helpDialogOpen: false }
    default:
      return state
  }
}

/**
 * Preferences state reducer
 */
function preferencesReducer(state: PreferencesState, action: AppAction): PreferencesState {
  switch (action.type) {
    case 'preferences/setSymbolStandard':
      return { ...state, symbolStandard: action.payload }
    case 'preferences/setTheme':
      return { ...state, theme: action.payload }
    case 'preferences/toggleShowGrid':
      return { ...state, showGrid: !state.showGrid }
    case 'preferences/toggleSnapToGrid':
      return { ...state, snapToGrid: !state.snapToGrid }
    case 'preferences/setGridSize':
      return { ...state, gridSize: action.payload }
    default:
      return state
  }
}

/**
 * Root reducer combining all state slices
 */
export function appReducer(state: AppState, action: AppAction): AppState {
  return {
    project: projectReducer(state.project, action),
    view: viewReducer(state.view, action),
    ui: uiReducer(state.ui, action),
    preferences: preferencesReducer(state.preferences, action),
  }
}
