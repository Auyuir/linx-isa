# ISA tools

## `build_golden.py`

Build the compiled machine-readable catalog from the multi-file golden sources:

- Golden sources: `isa/golden/v0.1/**`
- Compiled catalog (checked in): `isa/spec/current/linxisa-v0.1.json`

```bash
python3 tools/isa/build_golden.py --in isa/golden/v0.1 --out isa/spec/current/linxisa-v0.1.json --pretty
```

Use `--check` to verify the checked-in compiled catalog is up-to-date:

```bash
python3 tools/isa/build_golden.py --in isa/golden/v0.1 --out isa/spec/current/linxisa-v0.1.json --check
```

## `split_compiled.py` (bootstrap / review)

Split a compiled catalog JSON back into opcode DSL files (for bootstrapping/review only):

```bash
python3 tools/isa/split_compiled.py --spec isa/spec/current/linxisa-v0.1.json --out isa/golden/v0.1
```

## `validate_spec.py`

Sanity-checks that the generated `mask`/`match`/`pattern` are internally consistent:

```bash
python3 tools/isa/validate_spec.py --spec isa/spec/current/linxisa-v0.1.json
```

## `gen_qemu_codec.py`

Generates QEMU decodetree-style codec tables in `isa/generated/codecs/`:

```bash
python3 tools/isa/gen_qemu_codec.py --spec isa/spec/current/linxisa-v0.1.json --out-dir isa/generated/codecs
```

The output is intended to be consumed by:
- assembler/disassembler
- emulator decoder
- RTL decode generation

The extractor also computes per-instruction `mask`/`match` + field bit ranges under `instructions[].encoding`,
which is directly usable for QEMU-style decode tables and LLVM TableGen generation.

## `gen_c_codec.py`

Generates a C header/source pair containing packed `mask/match` + field extraction metadata:

```bash
python3 tools/isa/gen_c_codec.py --spec isa/spec/current/linxisa-v0.1.json --out-dir isa/generated/codecs
```

This is intended as a convenient input for LLVM MC and binutils ports without requiring a JSON parser.

## `linxdisasm.py`

Reference decoder for quick sanity-checks against hex words:

```bash
python3 tools/isa/linxdisasm.py --hex 5316 000fcf87 25cc0f95
```

This uses the same `mask/match` + field extraction derived from the JSON spec.
