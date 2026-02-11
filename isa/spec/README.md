# Compiled ISA Catalog

This folder contains the **compiled** (machine-readable) LinxISA ISA catalog.

Source of truth is the multi-file golden tree:

- `isa/golden/v0.3/**` (stable current)
- `isa/golden/v0.2/**` (legacy stable)

The compiled output is checked in at:

- `isa/spec/current/linxisa-v0.3.json` (stable current)
- `isa/spec/current/linxisa-v0.2.json` (legacy stable)
- `isa/spec/v0.3/linxisa-v0.3.json` (staged snapshot path)

## Rebuild

```bash
python3 tools/isa/build_golden.py --profile v0.3 --pretty
python3 tools/isa/validate_spec.py --profile v0.3
python3 tools/isa/build_golden.py --profile v0.2 --pretty
python3 tools/isa/validate_spec.py --profile v0.2
```
