# Keyboard Shortcuts Reference

This document lists keyboard shortcuts available in the Circuit Schematic Viewer.

## Current Status

Keyboard shortcuts are planned but not yet implemented. The shortcuts below describe the intended functionality for future releases.

## Planned Shortcuts

### Navigation

| Shortcut   | Action                   |
| ---------- | ------------------------ |
| `+` or `=` | Zoom in                  |
| `-`        | Zoom out                 |
| `0`        | Reset zoom to 100%       |
| `F`        | Fit schematic to view    |
| Arrow keys | Pan the view             |
| `Home`     | Center view on schematic |

### Selection

| Shortcut    | Action                   |
| ----------- | ------------------------ |
| `Escape`    | Clear selection          |
| `A`         | Select all components    |
| `Tab`       | Cycle through components |
| `Shift+Tab` | Cycle backwards          |

### Display Options

| Shortcut | Action                  |
| -------- | ----------------------- |
| `G`      | Toggle grid visibility  |
| `L`      | Toggle net labels       |
| `V`      | Toggle component values |
| `S`      | Open settings dialog    |

### Filter Modes

| Shortcut | Action               |
| -------- | -------------------- |
| `1`      | Show all (no filter) |
| `2`      | Filter by nets       |
| `3`      | Filter by components |
| `4`      | Neighborhood view    |

### File Operations

| Shortcut | Action                                 |
| -------- | -------------------------------------- |
| `Ctrl+O` | Open file picker                       |
| `Ctrl+S` | Export current view (when implemented) |

## Implementation Notes

When implementing keyboard shortcuts, consider:

1. **Focus context**: Shortcuts should only activate when the canvas or app has focus
2. **Modifier keys**: Use `Ctrl/Cmd` for system-level operations, plain keys for view controls
3. **Accessibility**: Ensure all shortcuts have toolbar button equivalents
4. **Discoverability**: Show shortcuts in tooltips on toolbar buttons

## Future Enhancements

- Customizable keyboard shortcuts
- Vim-style navigation mode
- Quick search with `/` key
- Command palette with `Ctrl+K` or `Ctrl+P`
