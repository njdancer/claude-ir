# Circuit Schematic Viewer

A web application for visualizing and exploring electronic circuit schematics defined in the `circuit.md` format.

## Features

- **Visual Schematic Rendering**: Automatically layout and display circuit schematics with standard IEEE/IEC symbols
- **Interactive Exploration**: Pan, zoom, and navigate through circuit diagrams
- **Filtering**: View circuits by net, component, or neighborhood
- **Validation**: Real-time validation with error and warning detection
- **Dual Symbol Standards**: Toggle between IEEE and IEC symbol conventions

## Quick Start

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Run tests
pnpm test
```

## Usage

1. Open the viewer in your browser (default: http://localhost:5173)
2. Drag and drop a `.circuit.md` file onto the dropzone, or click to browse
3. The schematic will be automatically parsed, validated, and rendered
4. Use the toolbar to zoom and toggle display options
5. Use the sidebar to filter and explore the circuit

## Circuit.md Format

The viewer accepts files in the `circuit.md` markdown format:

```markdown
# My Circuit

[VCC]: net
[GND]: net
[R1]: resistor(10k)
[C1]: capacitor(100nF)

[VCC --- R1.1]
[R1.2 --- C1.1]
[C1.2 --- GND]
```

See the [circuit.md specification](../.claude/skills/circuit-md-skill/SKILL.md) for complete documentation.

## Architecture

The viewer is built with:

- **React** - UI framework
- **Vite** - Build tool and dev server
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Component library

### Core Modules

| Module        | Description                                    |
| ------------- | ---------------------------------------------- |
| `parser/`     | Parses circuit.md files into an AST            |
| `graph/`      | Converts AST to a circuit graph model          |
| `layout/`     | Auto-layout algorithms for schematic placement |
| `symbols/`    | SVG symbol definitions (IEEE/IEC)              |
| `validation/` | Circuit validation rules                       |
| `state/`      | React context and state management             |
| `components/` | React UI components                            |

## Testing

```bash
# Run unit tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run E2E tests
pnpm test:e2e

# Generate coverage report
pnpm test:coverage
```

## Development

### Project Structure

```
viewer/
├── src/
│   ├── parser/       # circuit.md parser
│   ├── graph/        # Circuit graph model
│   ├── layout/       # Auto-layout algorithms
│   ├── symbols/      # Schematic symbols
│   ├── validation/   # Validation rules
│   ├── state/        # State management
│   └── components/   # React components
├── tests/
│   ├── unit/         # Vitest unit tests
│   └── e2e/          # Playwright E2E tests
└── public/           # Static assets
```

### Code Quality

```bash
# Lint code
pnpm lint

# Format code
pnpm format

# Type check
pnpm typecheck
```

## API Documentation

- [Parser API](docs/parser-api.md)
- [Graph API](docs/graph-api.md)
- [Adding New Symbols](docs/adding-symbols.md)

## License

MIT
