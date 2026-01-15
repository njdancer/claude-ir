---
name: circuit-md
description: "Format for describing electronic circuits in markdown. Use when designing, documenting, or generating circuit schematics with AI assistance. Embeds structured circuit definitions (components, nets, connections) within prose explanations. Supports export to KiCad netlist format. Use for: (1) AI-assisted circuit design, (2) Documenting circuit topology with rationale, (3) Generating netlists for PCB tools, (4) Collaborative circuit reviews."
---

# circuit.md

A markdown format for describing circuits that is both human-readable and machine-parseable.

## Core Concept

Circuit definitions are embedded in prose using a distinctive `[bracket]` syntax. The prose captures design rationale; the structured elements capture topology.

```markdown
The MCU needs a 3.3V supply. We use an LM1117 for regulation.

[VIN]: net
[3V3]: net
[GND]: net

[U1]: lm1117(3.3V)

[VIN --- U1.VIN]
[U1.VOUT --- 3V3]
[U1.GND --- GND]

Input and output capacitors per datasheet:

[VIN --- 10µF --- GND]
[3V3 --- 10µF --- GND]
```

## File Structure

Optional YAML frontmatter, then markdown with embedded circuit elements:

```yaml
---
name: USB Power Supply
description: |
  5V to 3.3V regulation for ESP32.
  Nets: VIN (5V input), 3V3 (output), GND
---
```

## Syntax Reference

### Nets

Declare named electrical nodes:

```
[NET_NAME]: net
```

Examples: `[VCC]: net`, `[GND]: net`, `[SDA]: net`

### Components

Declare named component instances:

```
[REF]: component_type
[REF]: component_type(parameters)
[REF]: @./path/to/subcircuit.circuit.md
```

Examples:
```
[R1]: resistor(10kΩ)
[C1]: capacitor(100nF)
[U1]: esp32_wroom
[U2]: lm1117(3.3V)
[PWR]: @./power-supply.circuit.md
```

### Connections

Link endpoints (component pins or nets):

```
[endpoint --- endpoint]
```

Pin syntax:
- Named: `U1.VCC`, `U1.GPIO0`
- Numbered: `U1#1`, `R1#2`

Examples:
```
[U1.VCC --- VCC]
[U1.GND --- GND]
[R1.1 --- VCC]
[R1.2 --- U1.RESET]
```

### Inline Passives

Shorthand for anonymous two-terminal passives:

```
[endpoint --- value --- endpoint]
```

| Suffix | Component |
|--------|-----------|
| `Ω` or `R` | Resistor |
| `F` | Capacitor |
| `H` | Inductor |
| `A` | Fuse |

Examples:
```
[VCC --- 10kΩ --- U1.RESET]      # pull-up
[U1.VCC --- 100nF --- GND]       # decoupling cap
[IN --- 4.7µH --- OUT]           # inductor
```

Value formats: `10k`, `4.7k`, `100n`, `4k7` (= 4.7k), `2R2` (= 2.2)

### Properties (Optional)

Capture design parameters inline:

```
[key ==> value]
[PIN.key ==> value]
```

Examples:
```
The regulator has dropout of [dropout ==> 1.2V] at full load.
[U1.VIN.max_voltage ==> 15V]
```

## Sub-circuits

Reference other circuit.md files as components. All nets in the sub-circuit become accessible pins:

```
[PSU]: @./power-supply.circuit.md

[PSU.VIN --- VBUS]
[PSU.VOUT --- 3V3]
[PSU.GND --- GND]
```

## Workflow

1. **Design**: Write circuit.md iteratively, documenting rationale
2. **Validate**: Run parser to check syntax and references
3. **Export**: Generate KiCad netlist
4. **Layout**: Import netlist into KiCad, arrange schematic, route PCB

## Scripts

### Parse and Validate

```bash
python scripts/parse_circuit.py circuit.md
```

Outputs JSON representation or lists errors with line numbers.

### Export KiCad Netlist

```bash
python scripts/export_kicad.py circuit.md -o circuit.net
```

Creates netlist importable by KiCad. Requires a parts mapping file for footprints.

### Parts Mapping

Create `parts.yaml` to map abstract components to KiCad symbols/footprints:

```yaml
# parts.yaml
resistor:
  symbol: Device:R
  footprint: Resistor_SMD:R_0402_1005Metric

capacitor:
  symbol: Device:C
  footprint: Capacitor_SMD:C_0402_1005Metric

esp32_wroom:
  symbol: RF_Module:ESP32-WROOM-32
  footprint: RF_Module:ESP32-WROOM-32

lm1117:
  symbol: Regulator_Linear:LM1117-3.3
  footprint: Package_TO_SOT_SMD:SOT-223-3_TabPin2
```

## Writing Guidelines

When writing circuit.md files:

1. **Declare before use**: Nets and components must be declared before referenced in connections
2. **Group logically**: Organize by functional block (power, oscillator, I/O, etc.)
3. **Explain why**: The prose should capture design decisions, not just describe connections
4. **Name meaningfully**: Use descriptive net names (`MOTOR_PWM` not `NET1`)
5. **Keep hierarchy shallow**: Sub-circuits work best for truly reusable blocks

## Limitations

This format captures **topology only**—what connects to what. It deliberately excludes:

- Schematic layout (component positions, wire routing)
- PCB layout (trace routing, placement)
- Simulation directives
- ERC validation rules

These concerns are handled by downstream tools (KiCad, SPICE, etc.) after netlist export.
