# Compiled ISA Catalog

This folder contains the **compiled** (machine-readable) LinxISA ISA catalog.

Source of truth is the multi-file golden tree:

- `isa/golden/v0.1/**`

The compiled output is checked in at:

- `isa/spec/current/linxisa-v0.1.json`

## Rebuild

```bash
python3 tools/isa/build_golden.py --in isa/golden/v0.1 --out isa/spec/current/linxisa-v0.1.json
python3 tools/isa/validate_spec.py --spec isa/spec/current/linxisa-v0.1.json
```
