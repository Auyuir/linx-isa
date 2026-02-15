# LinxISA Repository Flow (v0.4)

The workspace is specification-first and submodule-first.

## Workspace Bootstrap

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

Pinned ecosystem repos:

- `compiler/llvm`
- `emulator/qemu`
- `kernel/linux`
- `rtl/LinxCore`
- `tools/pyCircuit`
- `lib/glibc`
- `lib/musl`

## Flow

1. ISA definition in `spec/isa/golden/v0.3/`
2. Compiled catalog in `spec/isa/spec/current/linxisa-v0.3.json`
3. Generated decode assets in `spec/isa/generated/codecs/`
4. Validation in AVS (`avs/`)
5. Cross-repo alignment through submodule pinning
6. Regression gating with `tools/regression/run.sh`
