<p align="center">
  <img src="docs/architecture/isa-manual/src/images/linxisa-logo.svg" alt="LinxISA logo" width="200" />
</p>

<h1 align="center">Linx Instruction Set Architecture</h1>

<p align="center"><strong>LinxISA</strong> is a specification-first ISA project with aligned software and hardware implementations.</p>

## Overview

LinxISA is a RISC-style instruction-set architecture developed with a single-source specification workflow. This
repository keeps the ISA definition, compiler/backend artifacts, emulator work, and RTL bring-up assets in one place to
reduce spec/implementation drift.

## Naming and Targets

- Official ISA name: **Linx Instruction Set Architecture (LinxISA)**
- Short name: **Linx**
- LLVM/MC architecture names: `linx32`, `linx64`

## Canonical Specification

The ISA source of truth is under `isa/`:

- Authoritative golden sources: `isa/golden/v0.3/**`
- Current compiled catalog: `isa/spec/current/linxisa-v0.3.json`
- Legacy catalogs (reference only): `isa/spec/current/linxisa-v0.2.json`, `isa/spec/current/linxisa-v0.1.json`

All tools and implementations in this repository should consume the compiled catalog to keep encoding and behavior
consistent.

## Quick Start

Run end-to-end regression:

```bash
bash tools/regression/run.sh
```

Optional tool overrides:

```bash
export CLANG=~/llvm-project/build-linxisa-clang/bin/clang
export LLD=~/llvm-project/build-linxisa-clang/bin/ld.lld
export QEMU=~/qemu/build-tci/qemu-system-linx64
bash tools/regression/run.sh
```

## Documentation

- ISA manual (AsciiDoc/PDF): `docs/architecture/isa-manual/`
- Bring-up planning and status: `docs/bringup/README.md`, `docs/bringup/PROGRESS.md`
- Architecture and project docs: `docs/architecture/`, `docs/project/`, `docs/reference/`

Build the ISA manual PDF:

```bash
cd docs/architecture/isa-manual
make pdf
```

## Repository Structure

- `isa/`: ISA golden sources, generated codecs, compiled catalogs
- `tools/isa/`: ISA extraction, generation, and validation tooling
- `compiler/`: compiler and backend integration assets
- `toolchain/`: assembler/linker/libc and related toolchain pieces
- `emulator/`: emulator integration and patches
- `models/`: reference/modeling assets
- `rtl/`: hardware RTL implementation
- `tests/`: runtime and integration tests
- `workloads/`: benchmarks and workload harnesses
- `docs/`: architecture, bring-up, reference, and project documentation

## Development Flow

1. Author or update ISA definitions in `isa/`
2. Regenerate/validate machine-readable artifacts
3. Align compiler, emulator, and RTL behavior to the catalog
4. Run regression and targeted tests
