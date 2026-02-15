# Encoding SVG Diagrams

This directory contains SVG encoding diagrams for all Linx ISA instructions.

## Generated Files

- **734 SVG files** generated from the ISA specification
- Each instruction has its own encoding diagram showing:
  - Bit positions (MSB to LSB)
  - Field names with their bit ranges
  - Color-coded segments for different field types

## Field Color Coding

- **Gray (#e0e0e0)**: Constant fields
- **Teal (#4ecdc4)**: Register fields (Rd, Rs1, Rs2, etc.)
- **Yellow (#ffe66d)**: Immediate fields (imm, uimm, shamt, etc.)
- **Purple (#c792ea)**: Function fields (func3, func7, etc.)
- **Red (#ff6b6b)**: Opcode fields

## File Naming Convention

- `enc_<mnemonic>.svg` - Main encoding for each mnemonic
- `enc_<mnemonic>_var<N>.svg` - Additional variants

## Regenerating

To regenerate the SVG encoding diagrams:

```bash
python3 tools/isa/gen_encoding_svg.py
```

To regenerate the instruction detail pages with embedded SVGs:

```bash
python3 tools/isa/gen_manual_adoc.py
```

## Integration

The SVGs are automatically embedded in the instruction detail pages (instruction_details.adoc) using AsciiDoc image directives:

```asciidoc
Encoding::
+
image::encodings/enc_<mnemonic>.svg[<mnemonic> encoding diagram,align="center"]
```
