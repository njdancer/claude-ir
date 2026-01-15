# Claude Code Guidelines

This document defines foundational principles and technical standards for development on the claude-ir project.

## Project Overview

This repository contains:
- **ESP32 IR Remote** - Hardware design for a smart AC remote control
- **circuit.md** - A markdown format for describing electronic circuits
- **Circuit Schematic Viewer** - Web application for visualizing circuit.md files

## Foundational Principles

### Test-Driven Development (TDD)

Follow the red-green-refactor cycle:

1. **Red**: Write a failing test that defines expected behavior
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Improve code quality while keeping tests green

Tests are not optional—they are the foundation of confident development. Write tests before implementation, not after.

### Continuous Integration

Every push triggers automated checks:
- Linting (ESLint)
- Formatting verification (Prettier)
- Unit tests (Vitest)
- E2E tests (Playwright)
- Build verification

Never merge code that fails CI. Fix issues locally before pushing.

### Regular Commits

Commit early and often with descriptive messages:
- Each commit should represent a single logical change
- Commit messages should explain *why*, not just *what*
- Push regularly to maintain backup and enable collaboration

### Continuous Refactoring

Code quality is maintained through constant improvement:
- Refactor when you see opportunities, not in dedicated "cleanup" phases
- Keep functions small and focused
- Extract common patterns into reusable utilities
- Delete dead code immediately—don't comment it out

### Simplicity Over Cleverness

- Write code that is easy to read and understand
- Prefer explicit over implicit
- Avoid premature optimization
- Don't add features or abstractions until they're needed

## Technology Standards

### Runtime & Package Management

| Tool | Purpose | Version |
|------|---------|---------|
| **mise** | Runtime version management | Latest |
| **Node.js** | JavaScript runtime | LTS (via mise) |
| **pnpm** | Package manager | Latest |

Use `mise` to ensure consistent Node.js versions across environments. The `.mise.toml` file pins the exact version.

### Build & Development

| Tool | Purpose |
|------|---------|
| **Vite** | Build tool and dev server |
| **TypeScript** | Type-safe JavaScript |
| **React** | UI framework |

### Styling

| Tool | Purpose |
|------|---------|
| **Tailwind CSS** | Utility-first CSS |
| **shadcn/ui** | Component library (copy-paste, not npm) |

Use Tailwind utilities directly in JSX. Extract components when patterns repeat. shadcn/ui components are copied into the project and customized as needed.

### Testing

| Tool | Purpose |
|------|---------|
| **Vitest** | Unit and integration tests |
| **Playwright** | End-to-end browser tests |

Target 80%+ coverage for core logic (parser, graph, validation). E2E tests cover critical user workflows.

### Code Quality

| Tool | Purpose |
|------|---------|
| **ESLint** | Linting and static analysis |
| **Prettier** | Code formatting |

Run `pnpm lint` and `pnpm format` before committing. Configure your editor to format on save.

## Project Structure

```
claude-ir/
├── hardware/           # Hardware design files
│   └── circuits/       # circuit.md schematic files
├── specs/              # Technical specifications
├── viewer/             # Circuit Schematic Viewer web app
│   ├── src/
│   │   ├── parser/     # circuit.md parser
│   │   ├── graph/      # Circuit graph model
│   │   ├── layout/     # Auto-layout algorithms
│   │   ├── symbols/    # Schematic symbols
│   │   ├── validation/ # Circuit validation
│   │   └── components/ # React UI components
│   ├── tests/
│   │   ├── unit/       # Vitest tests
│   │   └── e2e/        # Playwright tests
│   └── public/         # Static assets
├── .claude/            # Claude Code skills
└── src/                # ESP32 firmware (C++)
```

## Development Workflow

### Starting Work

```bash
cd viewer
mise install        # Ensure correct Node.js version
pnpm install        # Install dependencies
pnpm dev            # Start dev server
```

### Running Tests

```bash
pnpm test           # Run unit tests
pnpm test:watch     # Run tests in watch mode
pnpm test:e2e       # Run E2E tests
pnpm test:coverage  # Run with coverage report
```

### Code Quality

```bash
pnpm lint           # Check for lint errors
pnpm lint:fix       # Auto-fix lint errors
pnpm format         # Format all files
pnpm format:check   # Check formatting without changing
```

### Building

```bash
pnpm build          # Production build
pnpm preview        # Preview production build
```

## Feature Tracking

Features are tracked in `viewer/features.yaml`. Each feature has:
- **id**: Unique identifier (e.g., PARSE-001)
- **status**: planned | in_progress | completed | blocked | deferred
- **dependencies**: List of feature IDs that must be completed first
- **priority**: critical | high | medium | low

Update feature status as work progresses. This provides visibility into project progress and helps identify blockers.

## Commit Message Format

```
<type>: <short description>

<optional longer description>

<optional references to features or issues>
```

Types:
- **feat**: New feature
- **fix**: Bug fix
- **refactor**: Code change that neither fixes nor adds
- **test**: Adding or updating tests
- **docs**: Documentation only
- **chore**: Build, tooling, or auxiliary changes

Example:
```
feat: implement net-focused view filtering

Add ability to filter schematic view to show only components
connected to selected nets. Uses BFS traversal on circuit graph.

Implements GRAPH-013, UI-023
```

## Code Style

### TypeScript

- Use strict mode (`"strict": true` in tsconfig)
- Prefer interfaces over types for object shapes
- Use explicit return types on exported functions
- Avoid `any`—use `unknown` and narrow with type guards

### React

- Use functional components with hooks
- Prefer composition over prop drilling
- Keep components focused on single responsibility
- Extract hooks for reusable stateful logic

### Testing

- Name tests descriptively: "should X when Y"
- One assertion per test when practical
- Use factories for test data, not copy-paste
- Test behavior, not implementation details

## circuit.md Format Reference

Quick reference for the circuit description format:

```markdown
[NET_NAME]: net                    # Declare net
[REF]: component_type(params)      # Declare component
[REF]: @./path.circuit.md          # Sub-circuit reference
[A --- B]                          # Connection
[A --- value --- B]                # Inline passive
[key ==> value]                    # Property
```

See `.claude/skills/circuit-md-skill/SKILL.md` for complete documentation.
