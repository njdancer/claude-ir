#!/usr/bin/env python3
"""
Parse circuit.md files and extract circuit topology.

Usage:
    python parse_circuit.py circuit.md              # Parse and validate
    python parse_circuit.py circuit.md --json       # Output JSON
    python parse_circuit.py circuit.md --debug      # Show all parsed elements
"""

import re
import sys
import json
import argparse
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Net:
    name: str
    line: int


@dataclass
class Component:
    ref: str
    type: str
    params: list[str]
    line: int
    is_subcircuit: bool = False


@dataclass
class Connection:
    from_endpoint: str
    to_endpoint: str
    line: int
    inline_value: Optional[str] = None  # For inline passives


@dataclass
class Property:
    key: str
    value: str
    line: int


@dataclass
class ParseError:
    message: str
    line: int
    context: str


@dataclass
class Circuit:
    name: str = ""
    description: str = ""
    nets: dict[str, Net] = field(default_factory=dict)
    components: dict[str, Component] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
    properties: list[Property] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    
    # Counter for anonymous inline components
    _inline_counter: int = field(default=0, repr=False)
    
    def next_inline_ref(self, prefix: str) -> str:
        self._inline_counter += 1
        return f"__{prefix}{self._inline_counter}"


# Regex patterns
FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
NET_DECL_PATTERN = re.compile(r'^\[([A-Za-z0-9_][A-Za-z0-9_]*)\]:\s*net\s*$')
COMPONENT_DECL_PATTERN = re.compile(
    r'^\[([A-Za-z_][A-Za-z0-9_]*)\]:\s*(@?[A-Za-z0-9_./-]+)(?:\(([^)]*)\))?\s*$'
)
CONNECTION_PATTERN = re.compile(
    r'^\[([^\]]+)\s+---\s+([^\]]+)\]\s*$'
)
PROPERTY_PATTERN = re.compile(
    r'\[([A-Za-z_][A-Za-z0-9_.]*)\s*==>\s*([^\]]+)\]'
)

# Value patterns for inline passives
VALUE_PATTERN = re.compile(
    r'^(\d+(?:\.\d+)?[kKmMµunp]?|\d+[kKmMµunp]\d+)([ΩRFHAfha])$'
)


def parse_value(value_str: str) -> Optional[tuple[str, str]]:
    """Parse a passive value like '10kΩ' into (normalized_value, component_type)."""
    match = VALUE_PATTERN.match(value_str.strip())
    if not match:
        return None
    
    value, unit = match.groups()
    unit = unit.upper()
    
    # Map units to component types
    type_map = {
        'Ω': 'resistor', 'R': 'resistor',
        'F': 'capacitor',
        'H': 'inductor',
        'A': 'fuse'
    }
    
    # Handle Ω specially since it's not ASCII
    if unit == 'Ω' or unit == 'Ω'.upper():
        comp_type = 'resistor'
    else:
        comp_type = type_map.get(unit)
    
    if not comp_type:
        return None
    
    return (value_str.strip(), comp_type)


def parse_endpoint(endpoint: str) -> dict:
    """Parse an endpoint into its components."""
    endpoint = endpoint.strip()
    
    # Check for numbered pin: U1#3
    if '#' in endpoint:
        parts = endpoint.split('#', 1)
        return {'component': parts[0], 'pin': f'#{parts[1]}', 'type': 'numbered'}
    
    # Check for named pin: U1.VCC
    if '.' in endpoint:
        parts = endpoint.split('.', 1)
        return {'component': parts[0], 'pin': parts[1], 'type': 'named'}
    
    # Must be a net name
    return {'net': endpoint, 'type': 'net'}


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (metadata, remaining_content)."""
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}, content
    
    yaml_content = match.group(1)
    remaining = content[match.end():]
    
    # Simple YAML parsing (just key: value pairs and multiline strings)
    metadata = {}
    current_key = None
    current_value_lines = []
    
    for line in yaml_content.split('\n'):
        if line.startswith('  ') and current_key:
            # Continuation of multiline value
            current_value_lines.append(line.strip())
        elif ':' in line:
            # Save previous key if exists
            if current_key:
                metadata[current_key] = '\n'.join(current_value_lines).strip()
            
            # Parse new key
            key, _, value = line.partition(':')
            current_key = key.strip()
            value = value.strip()
            
            if value == '|':
                current_value_lines = []
            else:
                current_value_lines = [value] if value else []
    
    # Save last key
    if current_key:
        metadata[current_key] = '\n'.join(current_value_lines).strip()
    
    return metadata, remaining


def parse_circuit(content: str, filename: str = "circuit.md") -> Circuit:
    """Parse a circuit.md file and return a Circuit object."""
    circuit = Circuit()
    
    # Parse frontmatter
    metadata, body = parse_frontmatter(content)
    circuit.name = metadata.get('name', '')
    circuit.description = metadata.get('description', '')
    
    # Calculate line offset from frontmatter
    frontmatter_lines = len(content) - len(body)
    if frontmatter_lines > 0:
        frontmatter_lines = content[:len(content) - len(body)].count('\n')
    
    # Process line by line
    lines = body.split('\n')
    
    for i, line in enumerate(lines):
        line_num = i + 1 + frontmatter_lines
        stripped = line.strip()
        
        if not stripped:
            continue
        
        # Try to match net declaration
        match = NET_DECL_PATTERN.match(stripped)
        if match:
            name = match.group(1)
            if name in circuit.nets:
                circuit.errors.append(ParseError(
                    f"Duplicate net declaration: {name}",
                    line_num,
                    stripped
                ))
            else:
                circuit.nets[name] = Net(name=name, line=line_num)
            continue
        
        # Try to match component declaration
        match = COMPONENT_DECL_PATTERN.match(stripped)
        if match:
            ref = match.group(1)
            comp_type = match.group(2)
            params_str = match.group(3) or ""
            params = [p.strip() for p in params_str.split(',') if p.strip()]
            
            is_subcircuit = comp_type.startswith('@')
            
            if ref in circuit.components:
                circuit.errors.append(ParseError(
                    f"Duplicate component reference: {ref}",
                    line_num,
                    stripped
                ))
            else:
                circuit.components[ref] = Component(
                    ref=ref,
                    type=comp_type,
                    params=params,
                    line=line_num,
                    is_subcircuit=is_subcircuit
                )
            continue
        
        # Try to match connection
        match = CONNECTION_PATTERN.match(stripped)
        if match:
            left = match.group(1).strip()
            right = match.group(2).strip()
            
            # Check for inline passive (three-part connection)
            parts = [p.strip() for p in re.split(r'\s+---\s+', stripped[1:-1])]
            
            if len(parts) == 3:
                # Inline passive: [A --- 10kΩ --- B]
                left, value, right = parts
                parsed_value = parse_value(value)
                
                if parsed_value:
                    norm_value, comp_type = parsed_value
                    # Create anonymous component
                    anon_ref = circuit.next_inline_ref(comp_type[0].upper())
                    circuit.components[anon_ref] = Component(
                        ref=anon_ref,
                        type=comp_type,
                        params=[norm_value],
                        line=line_num,
                        is_subcircuit=False
                    )
                    # Create two connections
                    circuit.connections.append(Connection(
                        from_endpoint=left,
                        to_endpoint=f"{anon_ref}.1",
                        line=line_num
                    ))
                    circuit.connections.append(Connection(
                        from_endpoint=f"{anon_ref}.2",
                        to_endpoint=right,
                        line=line_num
                    ))
                else:
                    circuit.errors.append(ParseError(
                        f"Invalid passive value: {value}",
                        line_num,
                        stripped
                    ))
            elif len(parts) == 2:
                # Normal connection: [A --- B]
                circuit.connections.append(Connection(
                    from_endpoint=left,
                    to_endpoint=right,
                    line=line_num
                ))
            continue
        
        # Try to match inline properties
        for prop_match in PROPERTY_PATTERN.finditer(line):
            circuit.properties.append(Property(
                key=prop_match.group(1),
                value=prop_match.group(2).strip(),
                line=line_num
            ))
    
    # Validate references
    validate_references(circuit)
    
    return circuit


def validate_references(circuit: Circuit):
    """Check that all referenced components and nets are declared."""
    for conn in circuit.connections:
        for endpoint_str in [conn.from_endpoint, conn.to_endpoint]:
            endpoint = parse_endpoint(endpoint_str)
            
            if endpoint['type'] == 'net':
                if endpoint['net'] not in circuit.nets:
                    circuit.errors.append(ParseError(
                        f"Undefined net: {endpoint['net']}",
                        conn.line,
                        f"[{conn.from_endpoint} --- {conn.to_endpoint}]"
                    ))
            else:
                comp = endpoint['component']
                # Handle sub-circuit pin references like PSU.VIN
                base_comp = comp.split('.')[0] if '.' in comp else comp
                if base_comp not in circuit.components:
                    circuit.errors.append(ParseError(
                        f"Undefined component: {base_comp}",
                        conn.line,
                        f"[{conn.from_endpoint} --- {conn.to_endpoint}]"
                    ))


def circuit_to_dict(circuit: Circuit) -> dict:
    """Convert Circuit to a JSON-serializable dict."""
    return {
        'name': circuit.name,
        'description': circuit.description,
        'nets': {k: asdict(v) for k, v in circuit.nets.items()},
        'components': {k: asdict(v) for k, v in circuit.components.items()},
        'connections': [asdict(c) for c in circuit.connections],
        'properties': [asdict(p) for p in circuit.properties],
        'errors': [asdict(e) for e in circuit.errors]
    }


def main():
    parser = argparse.ArgumentParser(description='Parse circuit.md files')
    parser.add_argument('file', help='circuit.md file to parse')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--debug', action='store_true', help='Show debug info')
    args = parser.parse_args()
    
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    
    content = filepath.read_text()
    circuit = parse_circuit(content, filepath.name)
    
    if args.json:
        print(json.dumps(circuit_to_dict(circuit), indent=2))
    elif args.debug:
        print(f"Name: {circuit.name}")
        print(f"Description: {circuit.description[:50]}..." if circuit.description else "")
        print(f"\nNets ({len(circuit.nets)}):")
        for net in circuit.nets.values():
            print(f"  {net.name} (line {net.line})")
        print(f"\nComponents ({len(circuit.components)}):")
        for comp in circuit.components.values():
            params = f"({', '.join(comp.params)})" if comp.params else ""
            print(f"  {comp.ref}: {comp.type}{params} (line {comp.line})")
        print(f"\nConnections ({len(circuit.connections)}):")
        for conn in circuit.connections:
            print(f"  {conn.from_endpoint} --- {conn.to_endpoint} (line {conn.line})")
        print(f"\nProperties ({len(circuit.properties)}):")
        for prop in circuit.properties:
            print(f"  {prop.key} ==> {prop.value} (line {prop.line})")
    
    # Report errors
    if circuit.errors:
        print(f"\nErrors ({len(circuit.errors)}):", file=sys.stderr)
        for err in circuit.errors:
            print(f"  Line {err.line}: {err.message}", file=sys.stderr)
            print(f"    {err.context}", file=sys.stderr)
        sys.exit(1)
    else:
        if not args.json:
            print(f"\n✓ Parsed successfully: {len(circuit.nets)} nets, "
                  f"{len(circuit.components)} components, "
                  f"{len(circuit.connections)} connections")
        sys.exit(0)


if __name__ == '__main__':
    main()
