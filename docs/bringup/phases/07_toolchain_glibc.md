# Phase 7: Toolchain/glibc Bring-up

Primary scripts and patch stacks:

- `tools/libc/apply-glibc-patches.sh`
- `tools/libc/build-glibc.sh`
- `tools/libc/patches/glibc/0001-glibc-linx-machine-triplet.patch`
- `tools/libc/patches/glibc/0002-glibc-linx-sysdeps-bootstrap.patch`

Legacy compatibility path:

- `tools/glibc/bringup_linx64.sh` (wrapper to `tools/libc/build-glibc.sh`)

## Objective

Produce a reproducible glibc bring-up flow for `linx64-unknown-linux-gnu` directly from this repo.

## Role in the bring-up sequence

- This phase closes Linux userspace toolchain blockers after compiler/emulator/kernel basics.
- It is support work for phases 4-6 and does not replace RTL/Linux validation gates.

## Workflow

From repo root:

```bash
make libc-init
make libc-patch-glibc
make libc-build-glibc
```

Artifacts and logs:

- Build/install root: `out/libc/glibc/`
- Logs: `out/libc/glibc/logs/`
- Gate artifacts: `out/libc/glibc/install/lib/libc.so`, `out/libc/glibc/install/lib/crt1.o`

## Current gates

- `G1`: configure + build glibc gate targets (`csu/subdir_lib`, `csu/crt1.o`, `libc.so`)
- Build flow forces `-fuse-ld=lld` to avoid host linker incompatibilities on macOS.

## Exit criteria

- `G1` passes on the reference bring-up host/toolchain.
- Toolchain/libc no longer blocks Linux shell/userland gates.
- Remaining issues are tracked explicitly in `docs/bringup/libc_status.md`.
