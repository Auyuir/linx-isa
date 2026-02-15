# LinxISA Specification (v0.3)

`isa/` is the canonical specification root for the public LinxISA repository.

## Canonical Artifacts

- Source components: `isa/v0.3/{encoding,opcodes,registers,state,reconcile,meta.json}`
- Compiled catalog: `isa/v0.3/linxisa-v0.3.json`
- Generated codec tables: `isa/generated/codecs/`
- Sail model + coverage assets: `isa/sail/`

## Build + Validate

```bash
python3 tools/isa/build_golden.py --profile v0.3 --pretty
python3 tools/isa/validate_spec.py --profile v0.3
```

## Downstream Consumption

Compiler, emulator, and RTL integration MUST consume the compiled v0.3 catalog to avoid decode/semantic drift.

See also:

- `isa/generated/codecs/README.md`
