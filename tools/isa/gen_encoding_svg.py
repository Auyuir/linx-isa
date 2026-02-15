#!/usr/bin/env python3
"""
Generate SVG encoding diagrams for Linx ISA instructions.

This script parses the Linx ISA JSON spec and generates SVG encoding diagrams
for each instruction, showing bit positions, field names, and color-coded segments.

The SVG format is inspired by RISC-V encoding diagrams, showing:
- Bit positions from MSB to LSB
- Field names with their bit ranges
- Color-coded segments for different field types (const, register, immediate, opcode)
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

# Color scheme for different field types
COLORS = {
    'const': '#e0e0e0',      # Gray for constant fields
    'opcode': '#ff6b6b',     # Red for opcode
    'register': '#4ecdc4',   # Teal for register fields
    'immediate': '#ffe66d',  # Yellow for immediate fields
    'func': '#c792ea',       # Purple for function fields
    'reserved': '#f7f7f7',   # White for reserved bits
    'field_bg': '#ffffff',   # White background
    'border': '#333333',     # Dark border
    'text': '#333333',       # Dark text
    'bit_num': '#666666',    # Gray bit numbers
}

# Field type patterns to classify segments
FIELD_PATTERNS = {
    'register': ['RegDst', 'SrcL', 'SrcR', 'SrcD', 'SrcP', 'SrcZero', 'SrcBegin', 'SrcEnd', 
                 'DstBegin', 'DstEnd', 'RegSrc', 'DstTile', 'SrcTile'],
    'immediate': ['imm', 'simm', 'uimm', 'shamt', 'offset', 'uimm'],
    'func': ['func', 'Func', 'Type', '_Type'],
    'opcode': ['opcode', 'Opcode'],
}


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _mkdirp(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _classify_field(token: str) -> str:
    """Classify a field token to determine its type for color coding."""
    token_upper = token.upper()
    
    # Check for register patterns
    for pattern in FIELD_PATTERNS['register']:
        if pattern in token:
            return 'register'
    
    # Check for immediate patterns
    for pattern in FIELD_PATTERNS['immediate']:
        if pattern.lower() in token.lower():
            return 'immediate'
    
    # Check for function patterns
    for pattern in FIELD_PATTERNS['func']:
        if pattern in token:
            return 'func'
    
    # Check for opcode patterns
    for pattern in FIELD_PATTERNS['opcode']:
        if pattern in token:
            return 'opcode'
    
    return 'const'


def _parse_segment(segment: Dict[str, Any]) -> Tuple[int, int, str, str, Optional[int]]:
    """Parse a segment to extract bit range and token info.
    
    Returns: (msb, lsb, token, field_type, const_value)
    """
    lsb = int(segment.get('lsb', 0))
    msb = int(segment.get('msb', 0))
    token = str(segment.get('token', ''))
    
    # Check if this is a constant field
    const_info = segment.get('const')
    if const_info is not None:
        const_value = const_info.get('value')
        return (msb, lsb, token, 'const', const_value)
    
    # Classify non-constant fields
    field_type = _classify_field(token)
    return (msb, lsb, token, field_type, None)


def _get_field_label(token: str, const_value: Optional[int]) -> str:
    """Generate a label for a field."""
    if const_value is not None:
        # Format constant value
        width = int(re.search(r'(\d+)', token).group(1)) if re.search(r'(\d+)', token) else 1
        if width <= 3:
            return f"{const_value:b}".zfill(width)
        elif width <= 6:
            return f"0x{const_value:02x}"
        else:
            return f"0x{const_value:x}"
    return token


def _extract_fields_from_instruction(inst: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all fields from an instruction's encoding."""
    fields = []
    parts = inst.get('parts', [])
    
    for part in parts:
        segments = part.get('segments', [])
        for seg in segments:
            msb, lsb, token, field_type, const_value = _parse_segment(seg)
            fields.append({
                'msb': msb,
                'lsb': lsb,
                'token': token,
                'type': field_type,
                'const_value': const_value,
                'label': _get_field_label(token, const_value)
            })
    
    return fields


def _calculate_svg_dimensions(total_bits: int) -> Tuple[int, int]:
    """Calculate SVG dimensions based on total bit length."""
    # Base dimensions
    width = 800
    row_height = 28
    header_height = 25
    padding = 10
    
    # Calculate width based on bits (more bits = wider)
    if total_bits > 32:
        width = 900
    if total_bits > 64:
        width = 1000
    
    height = header_height + row_height + padding * 2
    
    return width, height


def _get_field_width_percentage(field_bits: int, total_bits: int, svg_width: int) -> float:
    """Calculate the width percentage for a field based on its bit count."""
    # Leave some margin for labels
    available_width = svg_width - 200  # Reserve space for bit numbers and labels
    return (field_bits / total_bits) * available_width


def generate_encoding_svg(inst: Dict[str, Any], total_bits: int = 32) -> str:
    """Generate SVG encoding diagram for a single instruction."""
    
    fields = _extract_fields_from_instruction(inst)
    mnemonic = inst.get('mnemonic', 'UNKNOWN')
    
    # Calculate dimensions
    width, height = _calculate_svg_dimensions(total_bits)
    
    # SVG header
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" class="encoding-diagram">',
        f'  <defs>',
        f'    <style>',
        f'      .encoding-diagram {{ font-family: "Courier New", monospace; }}',
        f'      .bit-num {{ font-size: 10px; fill: {COLORS["bit_num"]}; text-anchor: middle; }}',
        f'      .field-label {{ font-size: 11px; fill: {COLORS["text"]}; text-anchor: middle; dominant-baseline: middle; }}',
        f'      .field-rect {{ stroke: {COLORS["border"]}; stroke-width: 0.5; }}',
        f'    </style>',
        f'  </defs>',
    ]
    
    # Background
    svg_lines.append(f'  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>')
    
    # Header with bit numbers
    header_y = 20
    bit_spacing = (width - 100) / (total_bits - 1) if total_bits > 1 else 0
    
    for i in range(total_bits):
        x = 50 + i * bit_spacing
        bit_pos = total_bits - 1 - i
        svg_lines.append(f'  <text x="{x}" y="{header_y}" class="bit-num">{bit_pos}</text>')
    
    # Draw field rectangles and labels
    row_y = 35
    current_x = 50
    
    # Sort fields by msb (descending)
    sorted_fields = sorted(fields, key=lambda f: f['msb'], reverse=True)
    
    # Group consecutive fields
    for field in sorted_fields:
        field_width = _get_field_width_percentage(field['msb'] - field['lsb'] + 1, total_bits, width)
        color = COLORS.get(field['type'], COLORS['const'])
        
        # Draw field rectangle
        svg_lines.append(
            f'  <rect x="{current_x}" y="{row_y}" width="{field_width}" height="25" '
            f'fill="{color}" class="field-rect"/>'
        )
        
        # Draw field label (if width is sufficient)
        if field_width > 25:
            label = field['label'] if field['label'] else f"{field['msb']}:{field['lsb']}"
            # Truncate long labels
            if len(label) > 12:
                label = label[:10] + '..'
            svg_lines.append(
                f'  <text x="{current_x + field_width/2}" y="{row_y + 12.5}" class="field-label">{label}</text>'
            )
        
        current_x += field_width + 2  # Small gap between fields
    
    # Draw separator line
    svg_lines.append(
        f'  <line x1="45" y1="{row_y + 27}" x2="{width - 10}" y2="{row_y + 27}" '
        f'stroke="{COLORS["border"]}" stroke-width="0.5"/>'
    )
    
    # Instruction name at the bottom
    svg_lines.append(
        f'  <text x="{width/2}" y="{height - 8}" font-size="12" font-weight="bold" '
        f'text-anchor="middle" fill="{COLORS["text"]}">{mnemonic}</text>'
    )
    
    svg_lines.append('</svg>')
    
    return '\n'.join(svg_lines)


def generate_encoding_table_svg(inst: Dict[str, Any], total_bits: int = 32) -> str:
    """Generate a more detailed SVG encoding table with explicit bit layout.
    
    This version shows a more detailed table-style layout similar to RISC-V manuals.
    """
    
    fields = _extract_fields_from_instruction(inst)
    mnemonic = inst.get('mnemonic', 'UNKNOWN')
    length_bits = inst.get('length_bits', total_bits)
    
    # Calculate dimensions
    row_height = 22
    header_height = 30
    legend_height = 25
    padding = 10
    
    # Width based on complexity
    width = 850
    if length_bits > 32:
        width = 950
    if length_bits > 48:
        width = 1050
        
    # Count unique positions for height
    num_rows = 2  # Bit numbers row + fields row
    height = header_height + num_rows * row_height + legend_height + padding * 2
    
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" class="encoding-table">',
        f'  <defs>',
        f'    <style>',
        f'      .encoding-table {{ font-family: "DejaVu Sans Mono", "Courier New", monospace; }}',
        f'      .bit-num {{ font-size: 9px; fill: #666; text-anchor: middle; }}',
        f'      .field-name {{ font-size: 10px; fill: #333; text-anchor: middle; dominant-baseline: middle; font-weight: bold; }}',
        f'      .field-value {{ font-size: 9px; fill: #555; text-anchor: middle; dominant-baseline: middle; }}',
        f'      .opcode-text {{ font-size: 10px; fill: #fff; text-anchor: middle; dominant-baseline: middle; font-weight: bold; }}',
        f'      .title {{ font-size: 14px; fill: #333; text-anchor: start; font-weight: bold; }}',
        f'      .legend-text {{ font-size: 9px; fill: #333; text-anchor: start; }}',
        f'      .encoding-diagram rect {{ stroke: #333; stroke-width: 0.5; }}',
        f'    </style>',
        f'  </defs>',
    ]
    
    # Background
    svg_lines.append(f'  <rect x="0" y="0" width="{width}" height="{height}" fill="white"/>')
    
    # Title
    svg_lines.append(f'  <text x="10" y="20" class="title">{mnemonic} ({length_bits}-bit)</text>')
    
    # Calculate bit spacing
    draw_width = width - 100
    bit_spacing = draw_width / length_bits
    
    header_y = 35
    row_y = header_y + row_height
    
    # Draw bit numbers (top row)
    for i in range(length_bits):
        x = 50 + (i + 0.5) * bit_spacing
        bit_pos = length_bits - 1 - i
        # Only show some bit numbers to avoid clutter
        if length_bits <= 32 or i % 4 == 0:
            svg_lines.append(f'  <text x="{x}" y="{header_y + 15}" class="bit-num">{bit_pos}</text>')
    
    # Draw field boxes (bottom row)
    current_pos = 0
    
    # Group fields by their position
    for field in sorted(fields, key=lambda f: f['msb'], reverse=True):
        field_width_bits = field['msb'] - field['lsb'] + 1
        field_start_pos = field['lsb']
        
        # Draw field rectangle
        x = 50 + field_start_pos * bit_spacing
        field_pixel_width = field_width_bits * bit_spacing
        
        color = COLORS.get(field['type'], COLORS['const'])
        
        # Draw the field box
        svg_lines.append(
            f'  <rect x="{x}" y="{row_y}" width="{field_pixel_width}" height="{row_height - 2}" '
            f'fill="{color}" rx="2"/>'
        )
        
        # Draw field name
        label = field['token']
        # Shorten long names
        if len(label) > 15:
            label = label[:12] + '...'
        
        if field_pixel_width > 30:
            svg_lines.append(
                f'  <text x="{x + field_pixel_width/2}" y="{row_y + row_height/2 - 3}" '
                f'class="field-name">{label}</text>'
            )
            # Show value if it's a constant
            if field['const_value'] is not None:
                val_label = field['label']
                if len(val_label) > 8:
                    val_label = val_label[:6] + '..'
                svg_lines.append(
                    f'  <text x="{x + field_pixel_width/2}" y="{row_y + row_height/2 + 7}" '
                    f'class="field-value">{val_label}</text>'
                )
        elif field_pixel_width > 15:
            # Just show abbreviated name
            svg_lines.append(
                f'  <text x="{x + field_pixel_width/2}" y="{row_y + row_height/2}" '
                f'class="field-name" font-size="8">{label[:4]}</text>'
            )
    
    # Draw border lines
    svg_lines.append(
        f'  <line x1="50" y1="{header_y}" x2="{width-50}" y2="{header_y}" stroke="#333" stroke-width="1"/>'
    )
    svg_lines.append(
        f'  <line x1="50" y1="{row_y}" x2="{width-50}" y2="{row_y}" stroke="#333" stroke-width="1"/>'
    )
    svg_lines.append(
        f'  <line x1="50" y1="{row_y + row_height}" x2="{width-50}" y2="{row_y + row_height}" stroke="#333" stroke-width="1"/>'
    )
    svg_lines.append(
        f'  <line x1="50" y1="{header_y}" x2="50" y2="{row_y + row_height}" stroke="#333" stroke-width="1"/>'
    )
    svg_lines.append(
        f'  <line x1="{width-50}" y1="{header_y}" x2="{width-50}" y2="{row_y + row_height}" stroke="#333" stroke-width="1"/>'
    )
    
    # Legend at bottom
    legend_y = height - 18
    legend_items = [
        ('const', 'Constant'),
        ('register', 'Register'),
        ('immediate', 'Immediate'),
        ('func', 'Function'),
    ]
    
    legend_x = 50
    for ftype, label in legend_items:
        svg_lines.append(f'  <rect x="{legend_x}" y="{legend_y}" width="12" height="12" fill="{COLORS[ftype]}" rx="1"/>')
        svg_lines.append(f'  <text x="{legend_x + 15}" y="{legend_y + 10}" class="legend-text">{label}</text>')
        legend_x += 100
    
    svg_lines.append('</svg>')
    
    return '\n'.join(svg_lines)


def generate_all_svg(spec: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    """Generate SVG encoding diagrams for all instructions in the spec.
    
    Returns a dictionary mapping instruction IDs to SVG content.
    """
    
    instructions = spec.get('instructions', [])
    svg_map = {}
    
    # Group by mnemonic for cleaner output
    mnemonics = {}
    for inst in instructions:
        mnem = inst.get('mnemonic', 'UNKNOWN')
        if mnem not in mnemonics:
            mnemonics[mnem] = []
        mnemonics[mnem].append(inst)
    
    print(f"Generating SVGs for {len(mnemonics)} unique mnemonics...")
    
    for mnemonic, insts in mnemonics.items():
        # Use the first variant for the main SVG (most common case)
        inst = insts[0]
        inst_id = inst.get('id', mnemonic.lower())
        length_bits = inst.get('length_bits', 32)
        
        # Generate the detailed encoding table SVG
        svg_content = generate_encoding_table_svg(inst, length_bits)
        
        # Save SVG file
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', mnemonic.lower())
        filename = f"enc_{safe_name}.svg"
        filepath = os.path.join(out_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        svg_map[mnemonic] = filename
        
        if len(insts) > 1:
            # For instructions with multiple variants, also generate variant SVGs
            for i, variant in enumerate(insts[1:], 1):
                var_id = variant.get('id', f"{mnemonic.lower()}_{i}")
                var_length = variant.get('length_bits', 32)
                var_svg = generate_encoding_table_svg(variant, var_length)
                
                var_filename = f"enc_{safe_name}_var{i}.svg"
                var_filepath = os.path.join(out_dir, var_filename)
                
                with open(var_filepath, 'w', encoding='utf-8') as f:
                    f.write(var_svg)
    
    print(f"Generated {len(svg_map)} SVG files in {out_dir}")
    
    return svg_map


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--spec",
        default="spec/isa/spec/current/linxisa-v0.3.json",
        help="Path to ISA catalog JSON"
    )
    ap.add_argument(
        "--out-dir",
        default="docs/architecture/isa-manual/src/generated/encodings",
        help="Output directory for SVG files"
    )
    args = ap.parse_args(args=argv)
    
    # Read the spec
    spec = _read_json(args.spec)
    
    # Create output directory
    _mkdirp(args.out_dir)
    
    # Generate SVGs
    svg_map = generate_all_svg(spec, args.out_dir)
    
    # Print summary
    print(f"\nGenerated encoding SVGs for {len(svg_map)} instructions")
    print(f"Output directory: {args.out_dir}")
    
    # List first few files
    print("\nSample files:")
    for i, (mnem, filename) in enumerate(list(svg_map.items())[:5]):
        print(f"  {mnem}: {filename}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
