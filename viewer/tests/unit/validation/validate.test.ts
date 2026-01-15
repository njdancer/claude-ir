import { describe, it, expect } from 'vitest'
import { validate } from '@/validation/validate'
import { parse } from '@/parser'
import { buildGraph } from '@/graph'

describe('validation', () => {
  describe('syntax validation', () => {
    it('should pass for valid circuit', () => {
      const ast = parse(
        `[VCC]: net
[U1]: esp32
[U1.VCC --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      expect(result.hasErrors).toBe(false)
    })
  })

  describe('reference validation', () => {
    it('should warn on undeclared net usage', () => {
      const ast = parse(
        `[U1]: esp32
[U1.VCC --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      // VCC is used but not declared
      const issue = result.issues.find(
        (i) => i.category === 'reference' && i.message.includes('VCC')
      )
      expect(issue).toBeDefined()
      expect(issue?.severity).toBe('warning')
    })

    it('should warn on undeclared component pin reference', () => {
      const ast = parse(
        `[VCC]: net
[U1.VCC --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      // U1 is used but not declared
      const issue = result.issues.find(
        (i) => i.category === 'reference' && i.message.includes('U1')
      )
      expect(issue).toBeDefined()
    })
  })

  describe('duplicate detection', () => {
    it('should report duplicate net declarations', () => {
      const ast = parse(
        `[VCC]: net
[VCC]: net`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      const issue = result.issues.find((i) => i.category === 'duplicate')
      expect(issue).toBeDefined()
    })

    it('should report duplicate component declarations', () => {
      const ast = parse(
        `[U1]: esp32
[U1]: atmega`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      const issue = result.issues.find((i) => i.category === 'duplicate')
      expect(issue).toBeDefined()
      expect(issue?.severity).toBe('error')
    })
  })

  describe('connectivity validation', () => {
    it('should warn on single-connection nets', () => {
      const ast = parse(
        `[VCC]: net
[U1]: esp32
[U1.VCC --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      // VCC only has one connection
      const issue = result.issues.find(
        (i) =>
          i.category === 'connectivity' &&
          i.message.toLowerCase().includes('single') &&
          i.message.includes('VCC')
      )
      expect(issue).toBeDefined()
      expect(issue?.severity).toBe('warning')
    })

    it('should warn on floating nets', () => {
      const ast = parse(
        `[VCC]: net
[UNUSED]: net
[U1]: esp32
[U1.VCC --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      // UNUSED is declared but never connected
      const issue = result.issues.find(
        (i) =>
          i.category === 'connectivity' &&
          i.message.toLowerCase().includes('unused') &&
          i.message.includes('UNUSED')
      )
      expect(issue).toBeDefined()
    })

    it('should not warn on properly connected nets', () => {
      const ast = parse(
        `[VCC]: net
[U1]: esp32
[U2]: sensor
[U1.VCC --- VCC]
[U2.VCC --- VCC]`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      // VCC has two connections, should be fine
      const singleConnIssue = result.issues.find(
        (i) =>
          i.category === 'connectivity' &&
          i.message.toLowerCase().includes('single') &&
          i.message.includes('VCC')
      )
      expect(singleConnIssue).toBeUndefined()
    })
  })

  describe('result structure', () => {
    it('should group issues by file', () => {
      const ast = parse(
        `[VCC]: net
[VCC]: net`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      expect(result.byFile.has('test.circuit.md')).toBe(true)
    })

    it('should group issues by severity', () => {
      const ast = parse(
        `[U1]: esp32
[U1]: esp32`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      expect(result.bySeverity.error.length).toBeGreaterThan(0)
    })

    it('should count issues correctly', () => {
      const ast = parse(
        `[U1]: esp32
[U1]: esp32
[UNUSED]: net`,
        'test.circuit.md'
      )
      const graph = buildGraph(ast)
      const result = validate(ast, graph)

      expect(result.counts.total).toBeGreaterThan(0)
      expect(result.counts.total).toBe(
        result.counts.error + result.counts.warning + result.counts.info
      )
    })
  })
})
