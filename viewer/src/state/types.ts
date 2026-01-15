import type { CircuitAST } from '@/parser'
import type { CircuitGraph } from '@/graph'
import type { ValidationResult } from '@/validation'
import type { LayoutResult } from '@/layout'
import type { SymbolStandard } from '@/symbols'

/**
 * Filter mode for the schematic view
 */
export type FilterMode = 'all' | 'net' | 'component' | 'neighborhood'

/**
 * Active filter configuration
 */
export interface FilterConfig {
  /** Filter mode */
  mode: FilterMode
  /** Selected net names (for net filter) */
  nets: string[]
  /** Selected component refs (for component filter) */
  components: string[]
  /** Center component for neighborhood filter */
  neighborhoodCenter: string | null
  /** Depth for neighborhood filter */
  neighborhoodDepth: number
}

/**
 * Viewport transform state
 */
export interface ViewportTransform {
  /** Horizontal pan offset */
  panX: number
  /** Vertical pan offset */
  panY: number
  /** Zoom level (1 = 100%) */
  zoom: number
}

/**
 * Selection state
 */
export interface SelectionState {
  /** Selected node IDs */
  selectedNodes: Set<string>
  /** Hovered node ID */
  hoveredNode: string | null
  /** Selected edge IDs */
  selectedEdges: Set<string>
}

/**
 * Project state - loaded circuit data
 */
export interface ProjectState {
  /** Source filename */
  filename: string | null
  /** Raw source content */
  sourceContent: string | null
  /** Parsed AST */
  ast: CircuitAST | null
  /** Built graph */
  graph: CircuitGraph | null
  /** Validation result */
  validation: ValidationResult | null
  /** Layout result */
  layout: LayoutResult | null
  /** Loading state */
  loading: boolean
  /** Error message if any */
  error: string | null
}

/**
 * View state - visualization configuration
 */
export interface ViewState {
  /** Active filter configuration */
  filter: FilterConfig
  /** Viewport transform */
  viewport: ViewportTransform
  /** Selection state */
  selection: SelectionState
  /** Whether to show validation issues */
  showValidation: boolean
  /** Whether to show net labels */
  showNetLabels: boolean
  /** Whether to show component values */
  showValues: boolean
}

/**
 * UI state - panel and dialog visibility
 */
export interface UIState {
  /** Whether sidebar is visible */
  sidebarVisible: boolean
  /** Whether file panel is visible */
  filePanelVisible: boolean
  /** Whether validation panel is visible */
  validationPanelVisible: boolean
  /** Whether settings dialog is open */
  settingsDialogOpen: boolean
  /** Whether help dialog is open */
  helpDialogOpen: boolean
}

/**
 * User preferences
 */
export interface PreferencesState {
  /** Symbol standard (IEEE/IEC) */
  symbolStandard: SymbolStandard
  /** Theme (light/dark/system) */
  theme: 'light' | 'dark' | 'system'
  /** Grid visibility */
  showGrid: boolean
  /** Grid snap enabled */
  snapToGrid: boolean
  /** Grid size in pixels */
  gridSize: number
}

/**
 * Complete application state
 */
export interface AppState {
  project: ProjectState
  view: ViewState
  ui: UIState
  preferences: PreferencesState
}

/**
 * Action types for state updates
 */
export type AppAction =
  // Project actions
  | { type: 'project/load'; payload: { filename: string; content: string } }
  | { type: 'project/setAST'; payload: CircuitAST }
  | { type: 'project/setGraph'; payload: CircuitGraph }
  | { type: 'project/setValidation'; payload: ValidationResult }
  | { type: 'project/setLayout'; payload: LayoutResult }
  | { type: 'project/setError'; payload: string }
  | { type: 'project/clear' }
  // View actions
  | { type: 'view/setFilter'; payload: Partial<FilterConfig> }
  | { type: 'view/resetFilter' }
  | { type: 'view/setViewport'; payload: Partial<ViewportTransform> }
  | { type: 'view/resetViewport' }
  | { type: 'view/selectNodes'; payload: string[] }
  | { type: 'view/toggleNodeSelection'; payload: string }
  | { type: 'view/clearSelection' }
  | { type: 'view/setHoveredNode'; payload: string | null }
  | { type: 'view/toggleShowValidation' }
  | { type: 'view/toggleShowNetLabels' }
  | { type: 'view/toggleShowValues' }
  // UI actions
  | { type: 'ui/toggleSidebar' }
  | { type: 'ui/toggleFilePanel' }
  | { type: 'ui/toggleValidationPanel' }
  | { type: 'ui/openSettingsDialog' }
  | { type: 'ui/closeSettingsDialog' }
  | { type: 'ui/openHelpDialog' }
  | { type: 'ui/closeHelpDialog' }
  // Preferences actions
  | { type: 'preferences/setSymbolStandard'; payload: SymbolStandard }
  | { type: 'preferences/setTheme'; payload: 'light' | 'dark' | 'system' }
  | { type: 'preferences/toggleShowGrid' }
  | { type: 'preferences/toggleSnapToGrid' }
  | { type: 'preferences/setGridSize'; payload: number }
