import { parse } from './parser'
import type { CircuitAST, SubcircuitNode } from './ast'
import type { ParseError } from './types'

/**
 * File loader interface for loading circuit.md files
 */
export interface FileLoader {
  /**
   * Load file content by path
   * @param path - Path to file (relative or absolute)
   * @param relativeTo - Base path for resolving relative paths
   * @returns File content or null if not found
   */
  load(path: string, relativeTo: string): Promise<string | null>

  /**
   * Resolve a relative path
   * @param path - Relative path
   * @param relativeTo - Base path
   * @returns Resolved absolute path
   */
  resolve(path: string, relativeTo: string): string
}

/**
 * Result of resolving a circuit
 */
export interface ResolveResult {
  /** Root circuit AST with resolved sub-circuits */
  ast: CircuitAST
  /** All loaded files (path -> AST) */
  files: Map<string, CircuitAST>
  /** All errors from all files */
  errors: ParseError[]
}

/**
 * Options for the resolver
 */
export interface ResolveOptions {
  /** Maximum recursion depth (default: 10) */
  maxDepth?: number
  /** Whether to resolve lazily (default: false) */
  lazy?: boolean
}

/**
 * Resolve all sub-circuit references in a circuit AST
 */
export async function resolve(
  rootContent: string,
  rootPath: string,
  loader: FileLoader,
  options: ResolveOptions = {}
): Promise<ResolveResult> {
  const maxDepth = options.maxDepth ?? 10
  const files = new Map<string, CircuitAST>()
  const errors: ParseError[] = []

  async function resolveCircuit(
    content: string,
    path: string,
    depth: number,
    resolutionChain: Set<string>
  ): Promise<CircuitAST> {
    // Check max depth
    if (depth > maxDepth) {
      errors.push({
        message: `Maximum sub-circuit depth exceeded (${maxDepth})`,
        location: { file: path, line: 1, column: 1 },
        severity: 'error',
      })
      return parse(content, path)
    }

    // Parse the circuit
    const ast = parse(content, path)
    files.set(path, ast)
    errors.push(...ast.errors)

    // Resolve sub-circuits (unless lazy)
    if (!options.lazy) {
      for (const [, subcircuit] of ast.subcircuits) {
        await resolveSubcircuit(subcircuit, path, depth, resolutionChain)
      }
    }

    return ast
  }

  async function resolveSubcircuit(
    subcircuit: SubcircuitNode,
    parentPath: string,
    depth: number,
    resolutionChain: Set<string>
  ): Promise<void> {
    const resolvedPath = loader.resolve(subcircuit.path, parentPath)

    // Check for circular reference BEFORE checking cache
    if (resolutionChain.has(resolvedPath)) {
      errors.push({
        message: `Circular sub-circuit reference detected: ${resolvedPath}`,
        location: subcircuit.location,
        severity: 'error',
      })
      return
    }

    // Check if already loaded (and not in current chain - so it's safe to reuse)
    if (files.has(resolvedPath)) {
      subcircuit.resolved = files.get(resolvedPath)
      return
    }

    // Load the file
    const content = await loader.load(subcircuit.path, parentPath)
    if (content === null) {
      errors.push({
        message: `Sub-circuit file not found: ${subcircuit.path}`,
        location: subcircuit.location,
        severity: 'error',
      })
      return
    }

    // Add to resolution chain for this branch
    const newChain = new Set(resolutionChain)
    newChain.add(resolvedPath)

    // Recursively resolve
    subcircuit.resolved = await resolveCircuit(content, resolvedPath, depth + 1, newChain)
  }

  // Start with root path in the chain
  const initialChain = new Set<string>([rootPath])
  const ast = await resolveCircuit(rootContent, rootPath, 0, initialChain)

  return { ast, files, errors }
}

/**
 * Create a file loader that uses a Map of pre-loaded files
 * Useful for testing and browser environments
 */
export function createMapLoader(fileMap: Map<string, string>): FileLoader {
  return {
    async load(path: string, relativeTo: string): Promise<string | null> {
      const resolved = this.resolve(path, relativeTo)
      return fileMap.get(resolved) ?? null
    },

    resolve(path: string, relativeTo: string): string {
      if (path.startsWith('./')) {
        // Get directory of relativeTo
        const dir = relativeTo.split('/').slice(0, -1).join('/')
        const resolved = dir ? `${dir}/${path.slice(2)}` : path.slice(2)
        // Normalize path
        return normalizePath(resolved)
      }
      return path
    },
  }
}

/**
 * Normalize a file path (resolve . and ..)
 */
function normalizePath(path: string): string {
  const parts = path.split('/')
  const result: string[] = []

  for (const part of parts) {
    if (part === '.' || part === '') continue
    if (part === '..') {
      result.pop()
    } else {
      result.push(part)
    }
  }

  return result.join('/')
}

/**
 * Get all unique component types used in a resolved circuit
 */
export function getComponentTypes(ast: CircuitAST, includeSubcircuits = true): Set<string> {
  const types = new Set<string>()

  for (const [, comp] of ast.components) {
    types.add(comp.componentType)
  }

  for (const passive of ast.inlinePassives) {
    types.add(passive.passiveType)
  }

  if (includeSubcircuits) {
    for (const [, sub] of ast.subcircuits) {
      if (sub.resolved) {
        const subTypes = getComponentTypes(sub.resolved, true)
        subTypes.forEach((t) => types.add(t))
      }
    }
  }

  return types
}

/**
 * Get all unique nets used in a resolved circuit
 */
export function getAllNets(ast: CircuitAST, includeSubcircuits = true): Set<string> {
  const nets = new Set<string>()

  for (const [name] of ast.nets) {
    nets.add(name)
  }

  if (includeSubcircuits) {
    for (const [ref, sub] of ast.subcircuits) {
      if (sub.resolved) {
        const subNets = getAllNets(sub.resolved, true)
        // Prefix with subcircuit ref
        subNets.forEach((n) => nets.add(`${ref}.${n}`))
      }
    }
  }

  return nets
}
