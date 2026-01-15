#!/usr/bin/env python3
"""
Export circuit.md to KiCad netlist format.

Usage:
    python export_kicad.py circuit.md -o circuit.net
    python export_kicad.py circuit.md -o circuit.net --parts parts.yaml
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Import parser from same directory
from parse_circuit import parse_circuit, parse_endpoint


def load_parts_mapping(parts_file: Path) -> dict:
    """Load parts.yaml mapping file."""
    if not parts_file.exists():
        return {}
    
    mapping = {}
    content = parts_file.read_text()
    
    current_key = None
    current_dict = {}
    
    for line in content.split('\n'):
        line = line.rstrip()
        if not line or line.startswith('#'):
            continue
        
        if not line.startswith(' ') and ':' in line:
            # Save previous entry
            if current_key:
                mapping[current_key] = current_dict
            
            # New top-level key
            key = line.split(':')[0].strip()
            current_key = key
            current_dict = {}
        elif line.startswith('  ') and ':' in line:
            # Property within current key
            prop_line = line.strip()
            prop_key, _, prop_val = prop_line.partition(':')
            current_dict[prop_key.strip()] = prop_val.strip()
    
    # Save last entry
    if current_key:
        mapping[current_key] = current_dict
    
    return mapping


def get_part_info(comp_type: str, params: list, parts_mapping: dict) -> tuple[str, str]:
    """Get KiCad symbol and footprint for a component."""
    # Strip @ prefix for subcircuits
    if comp_type.startswith('@'):
        comp_type = comp_type[1:]
    
    # Look up in parts mapping
    if comp_type in parts_mapping:
        info = parts_mapping[comp_type]
        return info.get('symbol', comp_type), info.get('footprint', '')
    
    # Default mappings for common primitives
    defaults = {
        'resistor': ('Device:R', 'Resistor_SMD:R_0402_1005Metric'),
        'capacitor': ('Device:C', 'Capacitor_SMD:C_0402_1005Metric'),
        'inductor': ('Device:L', 'Inductor_SMD:L_0402_1005Metric'),
        'led': ('Device:LED', 'LED_SMD:LED_0603_1608Metric'),
        'diode': ('Device:D', 'Diode_SMD:D_SOD-123'),
        'fuse': ('Device:Fuse', 'Fuse:Fuse_0603_1608Metric'),
    }
    
    if comp_type in defaults:
        return defaults[comp_type]
    
    # Return type as-is with no footprint
    return comp_type, ''


def build_netlist(circuit, parts_mapping: dict) -> dict:
    """Build netlist data structure from circuit."""
    # Initialize nets from declared nets
    nets = {name: set() for name in circuit.nets}
    
    # Process connections to build net membership
    for conn in circuit.connections:
        from_ep = parse_endpoint(conn.from_endpoint)
        to_ep = parse_endpoint(conn.to_endpoint)
        
        # Determine which net this connection belongs to
        net_name = None
        pins = []
        
        if from_ep['type'] == 'net':
            net_name = from_ep['net']
            if to_ep['type'] != 'net':
                pins.append((to_ep['component'], to_ep['pin']))
        elif to_ep['type'] == 'net':
            net_name = to_ep['net']
            pins.append((from_ep['component'], from_ep['pin']))
        else:
            # Both are component pins - create anonymous net or merge
            # For simplicity, create a net named after the connection
            net_name = f"Net_{conn.line}"
            pins.append((from_ep['component'], from_ep['pin']))
            pins.append((to_ep['component'], to_ep['pin']))
        
        if net_name not in nets:
            nets[net_name] = set()
        
        for pin in pins:
            nets[net_name].add(pin)
        
        # Also add net endpoints
        if from_ep['type'] == 'net' and to_ep['type'] == 'net':
            # Net-to-net connection (alias) - merge them
            # For now, just note both exist
            pass
    
    # Build component list with part info
    components = []
    for ref, comp in circuit.components.items():
        # Skip anonymous inline components from display ref but keep in netlist
        symbol, footprint = get_part_info(comp.type, comp.params, parts_mapping)
        value = comp.params[0] if comp.params else comp.type
        
        components.append({
            'ref': ref,
            'value': value,
            'symbol': symbol,
            'footprint': footprint,
            'type': comp.type
        })
    
    return {
        'components': components,
        'nets': {k: list(v) for k, v in nets.items() if v}  # Only non-empty nets
    }


def export_kicad_netlist(circuit, parts_mapping: dict) -> str:
    """Generate KiCad S-expression netlist."""
    netlist_data = build_netlist(circuit, parts_mapping)
    
    lines = []
    lines.append('(export (version "E")')
    lines.append(f'  (design')
    lines.append(f'    (source "{circuit.name or "circuit.md"}")')
    lines.append(f'    (date "{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}")')
    lines.append(f'    (tool "circuit.md exporter")')
    lines.append(f'  )')
    
    # Components section
    lines.append('  (components')
    for comp in netlist_data['components']:
        ref = comp['ref']
        value = comp['value']
        footprint = comp['footprint']
        
        lines.append(f'    (comp (ref "{ref}")')
        lines.append(f'      (value "{value}")')
        if footprint:
            lines.append(f'      (footprint "{footprint}")')
        lines.append(f'    )')
    lines.append('  )')
    
    # Nets section
    lines.append('  (nets')
    net_code = 0
    for net_name, pins in netlist_data['nets'].items():
        net_code += 1
        lines.append(f'    (net (code "{net_code}") (name "{net_name}")')
        for comp_ref, pin in pins:
            lines.append(f'      (node (ref "{comp_ref}") (pin "{pin}"))')
        lines.append(f'    )')
    lines.append('  )')
    
    lines.append(')')
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Export circuit.md to KiCad netlist')
    parser.add_argument('file', help='circuit.md file to export')
    parser.add_argument('-o', '--output', required=True, help='Output netlist file')
    parser.add_argument('--parts', help='Parts mapping YAML file', default='parts.yaml')
    args = parser.parse_args()
    
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    
    content = filepath.read_text()
    circuit = parse_circuit(content, filepath.name)
    
    if circuit.errors:
        print("Cannot export: circuit has errors", file=sys.stderr)
        for err in circuit.errors:
            print(f"  Line {err.line}: {err.message}", file=sys.stderr)
        sys.exit(1)
    
    # Load parts mapping
    parts_path = Path(args.parts)
    parts_mapping = load_parts_mapping(parts_path)
    if not parts_path.exists():
        print(f"Warning: Parts file not found: {parts_path}", file=sys.stderr)
        print("  Using default mappings for primitives", file=sys.stderr)
    
    # Generate and write netlist
    netlist = export_kicad_netlist(circuit, parts_mapping)
    
    output_path = Path(args.output)
    output_path.write_text(netlist)
    
    print(f"✓ Exported to {output_path}")
    print(f"  {len(circuit.components)} components")
    print(f"  {len(circuit.nets)} declared nets")


if __name__ == '__main__':
    main()
