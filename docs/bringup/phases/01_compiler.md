# Phase 1: Compiler Bring-up

Compiler implementation source of truth is the LLVM submodule:

- `compiler/llvm/`

In-repo compile validation assets are centralized under AVS:

- `avs/compiler/linx-llvm/tests/`

## Current checkpoint

- Host compiler binary commonly used: `~/llvm-project/build-linxisa-clang/bin/clang`
- Supported bring-up targets: `linx64-linx-none-elf`, `linx32-linx-none-elf`
- Compile test suite entrypoint: `avs/compiler/linx-llvm/tests/run.sh`

## Required invariants

- Encodings and decode assumptions must match `spec/isa/spec/current/linxisa-v0.3.json`.
- Block ISA control-flow invariants must hold.
- Call header adjacency rule (`BSTART CALL` + `SETRET`) must hold.

## Execution

```bash
CLANG=~/llvm-project/build-linxisa-clang/bin/clang ./avs/compiler/linx-llvm/tests/run.sh
```
