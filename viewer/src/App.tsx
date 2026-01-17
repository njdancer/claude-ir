import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AppStateProvider,
  useAppState,
  useProjectState,
  useViewState,
  useUIState,
  usePreferencesState,
  useFilter,
  useViewport,
  useSelection,
  selectNetNames,
  selectComponentRefs,
  selectFilteredGraph,
} from '@/state'
import { parse } from '@/parser'
import { buildGraph } from '@/graph'
import { validate } from '@/validation'
import { layoutGraphElk } from '@/layout'
import { SchematicCanvas } from '@/components/canvas/SchematicCanvas'
import { Toolbar } from '@/components/toolbar/Toolbar'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { FileDropzone } from '@/components/file/FileDropzone'
import { SettingsDialog } from '@/components/settings/SettingsDialog'
import { Button } from '@/components/ui/button'
import { PanelLeft, Play, ChevronDown } from 'lucide-react'
import { DEMO_CIRCUITS, loadDemoCircuit, createDemoFileLoader } from '@/demo'
import { resolve as resolveCircuit } from '@/parser/resolver'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import './App.css'

/**
 * Main application content
 */
function AppContent() {
  const { state, actions } = useAppState()
  const project = useProjectState()
  const view = useViewState()
  const ui = useUIState()
  const preferences = usePreferencesState()
  const { filter, setFilter, resetFilter } = useFilter()
  const { viewport, setViewport } = useViewport()
  const { selectedNodes, hoveredNode, setHoveredNode, toggleNodeSelection } = useSelection()

  // Derived data
  const netNames = useMemo(() => selectNetNames(state), [state])
  const componentRefs = useMemo(() => selectComponentRefs(state), [state])
  const filteredGraph = useMemo(() => selectFilteredGraph(state), [state])

  // Track what content we've started processing to prevent re-entry
  const processingContentRef = useRef<string | null>(null)

  // Process circuit file when loaded
  useEffect(() => {
    if (!project.sourceContent || !project.filename) return

    // Skip if we've already started processing this content
    if (processingContentRef.current === project.sourceContent) return

    // Mark this content as being processed
    processingContentRef.current = project.sourceContent

    // Capture values for async function
    const sourceContent = project.sourceContent
    const filename = project.filename

    const processCircuit = async () => {
      try {
        // Parse
        const ast = parse(sourceContent, filename)
        actions.setAST(ast)

        // Build graph
        const graph = buildGraph(ast)
        actions.setGraph(graph)

        // Validate
        const validationResult = validate(ast, graph)
        actions.setValidation(validationResult)

        // Layout using ELK (async)
        const layoutResult = await layoutGraphElk(graph)
        actions.setLayout(layoutResult)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to process circuit'
        actions.setError(message)
      }
    }

    processCircuit()
  }, [project.sourceContent, project.filename, actions])

  // File load handler
  const handleFileLoad = useCallback(
    (filename: string, content: string) => {
      actions.loadProject(filename, content)
    },
    [actions]
  )

  // Pan handler
  const handlePan = useCallback(
    (deltaX: number, deltaY: number) => {
      setViewport({
        panX: viewport.panX + deltaX,
        panY: viewport.panY + deltaY,
      })
    },
    [viewport.panX, viewport.panY, setViewport]
  )

  // Zoom handler
  const handleZoom = useCallback(
    (delta: number) => {
      const newZoom = Math.max(0.1, Math.min(5, viewport.zoom + delta))
      setViewport({ zoom: newZoom })
    },
    [viewport.zoom, setViewport]
  )

  // Node click handler
  const handleNodeClick = useCallback(
    (nodeId: string) => {
      toggleNodeSelection(nodeId)
    },
    [toggleNodeSelection]
  )

  // Toolbar handlers
  const handleZoomIn = useCallback(() => handleZoom(0.1), [handleZoom])
  const handleZoomOut = useCallback(() => handleZoom(-0.1), [handleZoom])
  const handleZoomReset = useCallback(() => {
    setViewport({ panX: 0, panY: 0, zoom: 1 })
  }, [setViewport])

  // Demo loading state
  const [demoLoading, setDemoLoading] = useState(false)

  // Demo load handler with sub-circuit resolution
  const handleLoadDemo = useCallback(
    async (filename: string) => {
      setDemoLoading(true)
      try {
        const { content } = await loadDemoCircuit(filename)

        // Create a file loader for demo circuits and resolve sub-circuits
        const loader = createDemoFileLoader()
        const { ast, errors } = await resolveCircuit(content, filename, loader)

        // Report any resolution errors but continue
        if (errors.length > 0) {
          console.warn('Resolution errors:', errors)
        }

        actions.setAST(ast)

        // Build graph from resolved AST
        const graph = buildGraph(ast)
        actions.setGraph(graph)

        // Validate
        const validationResult = validate(ast, graph)
        actions.setValidation(validationResult)

        // Layout
        const layoutResult = await layoutGraphElk(graph)
        actions.setLayout(layoutResult)

        // Mark project as loaded
        actions.loadProject(filename, content)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load demo circuit'
        actions.setError(message)
      } finally {
        setDemoLoading(false)
      }
    },
    [actions]
  )

  // Show welcome screen if no project loaded
  const showWelcome = !project.filename && !project.loading && !demoLoading

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      {/* Toolbar */}
      <Toolbar
        zoom={viewport.zoom}
        showGrid={preferences.showGrid}
        showNetLabels={view.showNetLabels}
        showValues={view.showValues}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onZoomReset={handleZoomReset}
        onToggleGrid={actions.toggleShowGrid}
        onToggleNetLabels={actions.toggleShowNetLabels}
        onToggleValues={actions.toggleShowValues}
        onOpenSettings={actions.openSettingsDialog}
      />

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar toggle button */}
        {!ui.sidebarVisible && project.filename && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-16 left-4 z-10"
            onClick={actions.toggleSidebar}
          >
            <PanelLeft className="h-5 w-5" />
          </Button>
        )}

        {/* Sidebar */}
        {ui.sidebarVisible && project.filename && (
          <Sidebar
            filter={filter}
            netNames={netNames}
            componentRefs={componentRefs}
            validation={project.validation}
            filename={project.filename}
            sourceContent={project.sourceContent}
            onFilterChange={setFilter}
            onResetFilter={resetFilter}
            onClose={actions.toggleSidebar}
          />
        )}

        {/* Canvas area */}
        <div className="relative flex-1">
          {showWelcome ? (
            <div className="flex h-full items-center justify-center p-8">
              <div className="max-w-md space-y-6 text-center">
                <h1 className="text-2xl font-semibold text-slate-800">Circuit Schematic Viewer</h1>
                <p className="text-slate-600">
                  Drop a .circuit.md file to visualize and explore your circuit schematic.
                </p>
                <FileDropzone onFileLoad={handleFileLoad} className="h-48" />

                <div className="flex items-center justify-center gap-4 pt-2">
                  <span className="text-sm text-slate-500">or</span>
                </div>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="gap-2">
                      <Play className="h-4 w-4" />
                      Load Demo Circuit
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="center" className="w-64">
                    {DEMO_CIRCUITS.map((demo) => (
                      <DropdownMenuItem
                        key={demo.filename}
                        onClick={() => handleLoadDemo(demo.filename)}
                        className="flex flex-col items-start gap-1"
                      >
                        <span className="font-medium">{demo.name}</span>
                        <span className="text-xs text-slate-500">{demo.description}</span>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          ) : project.error ? (
            <div className="flex h-full items-center justify-center p-8">
              <div className="max-w-md space-y-4 text-center">
                <div className="text-red-500">
                  <p className="text-lg font-semibold">Error Loading Circuit</p>
                  <p className="text-sm">{project.error}</p>
                </div>
                <FileDropzone onFileLoad={handleFileLoad} className="h-32" />
              </div>
            </div>
          ) : (
            <SchematicCanvas
              graph={filteredGraph}
              layout={project.layout}
              selectedNodes={selectedNodes}
              hoveredNode={hoveredNode}
              showNetLabels={view.showNetLabels}
              showValues={view.showValues}
              showGrid={preferences.showGrid}
              gridSize={preferences.gridSize}
              zoom={viewport.zoom}
              panX={viewport.panX}
              panY={viewport.panY}
              onNodeClick={handleNodeClick}
              onNodeHover={setHoveredNode}
              onPan={handlePan}
              onZoom={handleZoom}
            />
          )}
        </div>
      </div>

      {/* Settings dialog */}
      <SettingsDialog
        open={ui.settingsDialogOpen}
        onOpenChange={(open) =>
          open ? actions.openSettingsDialog() : actions.closeSettingsDialog()
        }
        symbolStandard={preferences.symbolStandard}
        theme={preferences.theme}
        showGrid={preferences.showGrid}
        snapToGrid={preferences.snapToGrid}
        gridSize={preferences.gridSize}
        onSymbolStandardChange={actions.setSymbolStandard}
        onThemeChange={actions.setTheme}
        onShowGridChange={actions.toggleShowGrid}
        onSnapToGridChange={actions.toggleSnapToGrid}
        onGridSizeChange={actions.setGridSize}
      />
    </div>
  )
}

/**
 * Main App component with state provider
 */
function App() {
  return (
    <AppStateProvider>
      <AppContent />
    </AppStateProvider>
  )
}

export default App
