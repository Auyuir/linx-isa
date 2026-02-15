# Phase 2: ISA Spec Integration

Source of truth: `isa/v0.3/**` (compiled to `isa/v0.3/linxisa-v0.3.json`)

Supporting context:
- `isa/README.md`
- `isa/generated/codecs/` (generated decode/encode artifacts)

## Rule

Compiler, emulator, and RTL behavior must be derived from, or checked against, the same catalog.

## Regeneration

```bash
python3 tools/isa/build_golden.py --in isa/v0.3 --out isa/v0.3/linxisa-v0.3.json --pretty
python3 tools/isa/validate_spec.py --spec isa/v0.3/linxisa-v0.3.json
```
