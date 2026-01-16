/**
 * Demo circuit loading utilities
 */

export interface DemoCircuit {
  name: string
  filename: string
  description: string
}

/**
 * List of available demo circuits
 */
export const DEMO_CIRCUITS: DemoCircuit[] = [
  {
    name: 'ESP32 IR Remote (Full Project)',
    filename: 'esp32-ir-remote.circuit.md',
    description: 'Complete development board with all subcircuits',
  },
  {
    name: 'Power Supply',
    filename: 'power-supply.circuit.md',
    description: 'USB-C power with protection and 3.3V buck regulation',
  },
  {
    name: 'USB Serial Bridge',
    filename: 'usb-serial.circuit.md',
    description: 'CH340C USB-to-UART bridge with auto-reset',
  },
  {
    name: 'ESP32 MCU',
    filename: 'esp32-mcu.circuit.md',
    description: 'ESP32-WROOM module with boot configuration',
  },
  {
    name: 'IR Transmitter',
    filename: 'ir-transmitter.circuit.md',
    description: 'Four IR LEDs with MOSFET driver',
  },
  {
    name: 'IR Receiver',
    filename: 'ir-receiver.circuit.md',
    description: '38kHz IR receiver module',
  },
  {
    name: 'Temperature Sensor',
    filename: 'temp-sensor.circuit.md',
    description: 'DHT22 temperature/humidity sensor',
  },
  {
    name: 'Status LEDs',
    filename: 'status-leds.circuit.md',
    description: 'Serial activity and user indicators',
  },
]

/**
 * Load a demo circuit by filename
 */
export async function loadDemoCircuit(filename: string): Promise<{ filename: string; content: string }> {
  const response = await fetch(`/demo-circuits/${filename}`)
  if (!response.ok) {
    throw new Error(`Failed to load demo circuit: ${response.statusText}`)
  }
  const content = await response.text()
  return { filename, content }
}

/**
 * Load all demo circuits (for multi-file support)
 */
export async function loadAllDemoCircuits(): Promise<Map<string, string>> {
  const circuits = new Map<string, string>()

  for (const demo of DEMO_CIRCUITS) {
    try {
      const { content } = await loadDemoCircuit(demo.filename)
      circuits.set(demo.filename, content)
    } catch (error) {
      console.warn(`Failed to load ${demo.filename}:`, error)
    }
  }

  return circuits
}

/**
 * Create a FileLoader for demo circuits
 * This loader fetches files from /demo-circuits/ and caches them
 */
export function createDemoFileLoader(): {
  load: (path: string, relativeTo: string) => Promise<string | null>
  resolve: (path: string, relativeTo: string) => string
} {
  const cache = new Map<string, string>()

  return {
    async load(path: string, relativeTo: string): Promise<string | null> {
      const resolved = this.resolve(path, relativeTo)

      // Check cache first
      if (cache.has(resolved)) {
        return cache.get(resolved)!
      }

      // Fetch from demo-circuits
      try {
        const response = await fetch(`/demo-circuits/${resolved}`)
        if (!response.ok) {
          return null
        }
        const content = await response.text()
        cache.set(resolved, content)
        return content
      } catch {
        return null
      }
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
