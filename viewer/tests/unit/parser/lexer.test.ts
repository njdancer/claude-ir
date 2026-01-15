import { describe, it, expect } from 'vitest'
import { tokenize } from '@/parser/lexer'

describe('lexer', () => {
  describe('net declarations', () => {
    it('should tokenize a net declaration', () => {
      const input = '[VCC]: net'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      expect(result.tokens).toHaveLength(2) // NET_DECLARATION + EOF

      const token = result.tokens[0]
      expect(token.type).toBe('NET_DECLARATION')
      if (token.type === 'NET_DECLARATION') {
        expect(token.name).toBe('VCC')
      }
    })

    it('should tokenize multiple net declarations', () => {
      const input = `[VCC]: net
[GND]: net
[SDA]: net`
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const netTokens = result.tokens.filter((t) => t.type === 'NET_DECLARATION')
      expect(netTokens).toHaveLength(3)
    })

    it('should handle net names with underscores', () => {
      const input = '[USB_DP]: net'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      if (token.type === 'NET_DECLARATION') {
        expect(token.name).toBe('USB_DP')
      }
    })
  })

  describe('component declarations', () => {
    it('should tokenize a simple component', () => {
      const input = '[U1]: esp32_wroom'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      expect(token.type).toBe('COMPONENT_DECLARATION')
      if (token.type === 'COMPONENT_DECLARATION') {
        expect(token.ref).toBe('U1')
        expect(token.componentType).toBe('esp32_wroom')
        expect(token.params).toHaveLength(0)
      }
    })

    it('should tokenize a component with parameters', () => {
      const input = '[R1]: resistor(10kΩ)'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      if (token.type === 'COMPONENT_DECLARATION') {
        expect(token.ref).toBe('R1')
        expect(token.componentType).toBe('resistor')
        expect(token.params).toEqual(['10kΩ'])
      }
    })

    it('should tokenize a component with multiple parameters', () => {
      const input = '[U2]: lm1117(3.3V, SOT223)'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      if (token.type === 'COMPONENT_DECLARATION') {
        expect(token.params).toEqual(['3.3V', 'SOT223'])
      }
    })
  })

  describe('subcircuit references', () => {
    it('should tokenize a subcircuit reference', () => {
      const input = '[PSU]: @./power-supply.circuit.md'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      expect(token.type).toBe('SUBCIRCUIT_REFERENCE')
      if (token.type === 'SUBCIRCUIT_REFERENCE') {
        expect(token.ref).toBe('PSU')
        expect(token.path).toBe('./power-supply.circuit.md')
      }
    })
  })

  describe('connections', () => {
    it('should tokenize a simple connection', () => {
      const input = '[U1.VCC --- VCC]'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      expect(token.type).toBe('CONNECTION')
      if (token.type === 'CONNECTION') {
        expect(token.from).toBe('U1.VCC')
        expect(token.to).toBe('VCC')
      }
    })

    it('should tokenize a connection with numbered pins', () => {
      const input = '[R1#1 --- U1.RESET]'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      if (token.type === 'CONNECTION') {
        expect(token.from).toBe('R1#1')
        expect(token.to).toBe('U1.RESET')
      }
    })
  })

  describe('inline passives', () => {
    it('should tokenize a resistor inline passive', () => {
      const input = '[VCC --- 10kΩ --- U1.RESET]'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      expect(token.type).toBe('INLINE_PASSIVE')
      if (token.type === 'INLINE_PASSIVE') {
        expect(token.from).toBe('VCC')
        expect(token.value).toBe('10kΩ')
        expect(token.to).toBe('U1.RESET')
        expect(token.passiveType).toBe('resistor')
      }
    })

    it('should tokenize a capacitor inline passive', () => {
      const input = '[U1.VCC --- 100nF --- GND]'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      if (token.type === 'INLINE_PASSIVE') {
        expect(token.value).toBe('100nF')
        expect(token.passiveType).toBe('capacitor')
      }
    })

    it('should tokenize an inductor inline passive', () => {
      const input = '[IN --- 4.7µH --- OUT]'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      if (token.type === 'INLINE_PASSIVE') {
        expect(token.passiveType).toBe('inductor')
      }
    })

    it('should handle R suffix for resistors', () => {
      const input = '[VCC --- 4k7 --- EN]'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      if (token.type === 'INLINE_PASSIVE') {
        expect(token.passiveType).toBe('resistor')
      }
    })
  })

  describe('properties', () => {
    it('should tokenize a property', () => {
      const input = '[dropout ==> 1.2V]'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      expect(token.type).toBe('PROPERTY')
      if (token.type === 'PROPERTY') {
        expect(token.key).toBe('dropout')
        expect(token.value).toBe('1.2V')
      }
    })

    it('should tokenize a pin property', () => {
      const input = '[U1.VIN.max_voltage ==> 15V]'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const token = result.tokens[0]
      if (token.type === 'PROPERTY') {
        expect(token.key).toBe('U1.VIN.max_voltage')
        expect(token.value).toBe('15V')
      }
    })
  })

  describe('frontmatter', () => {
    it('should tokenize YAML frontmatter', () => {
      const input = `---
name: Power Supply
description: |
  5V to 3.3V regulation
---
[VCC]: net`
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)
      const frontmatter = result.tokens.find((t) => t.type === 'FRONTMATTER')
      expect(frontmatter).toBeDefined()
      if (frontmatter?.type === 'FRONTMATTER') {
        expect(frontmatter.content).toContain('name: Power Supply')
      }
    })
  })

  describe('mixed content', () => {
    it('should tokenize a realistic circuit snippet', () => {
      const input = `[VCC]: net
[GND]: net

[U1]: lm1117(3.3V)

[VIN --- U1.VIN]
[U1.VOUT --- VCC]
[U1.GND --- GND]

[VIN --- 10µF --- GND]`
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors).toHaveLength(0)

      const types = result.tokens.map((t) => t.type)
      expect(types.filter((t) => t === 'NET_DECLARATION')).toHaveLength(2)
      expect(types.filter((t) => t === 'COMPONENT_DECLARATION')).toHaveLength(1)
      expect(types.filter((t) => t === 'CONNECTION')).toHaveLength(3)
      expect(types.filter((t) => t === 'INLINE_PASSIVE')).toHaveLength(1)
    })
  })

  describe('source locations', () => {
    it('should track line numbers correctly', () => {
      const input = `[VCC]: net
[GND]: net`
      const result = tokenize(input, 'test.circuit.md')

      expect(result.tokens[0].location.line).toBe(1)
      expect(result.tokens[1].location.line).toBe(2)
    })

    it('should track column numbers correctly', () => {
      const input = 'Some text [VCC]: net'
      const result = tokenize(input, 'test.circuit.md')

      const netToken = result.tokens.find((t) => t.type === 'NET_DECLARATION')
      expect(netToken?.location.column).toBe(11)
    })
  })

  describe('error handling', () => {
    it('should report unclosed brackets', () => {
      const input = '[VCC: net'
      const result = tokenize(input, 'test.circuit.md')

      expect(result.errors.length).toBeGreaterThan(0)
      expect(result.errors[0].message).toContain('bracket')
    })
  })
})
