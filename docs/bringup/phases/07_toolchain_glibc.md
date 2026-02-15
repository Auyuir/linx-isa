# Phase 7: Toolchain/glibc Bring-up

Canonical source repository:

- `lib/glibc` (`git@github.com:LinxISA/glibc.git`)

## Objective

Track and validate Linx glibc bring-up for `linx64-unknown-linux-gnu` in the forked glibc repository.

## Role in the bring-up sequence

- This phase closes Linux userspace toolchain blockers after compiler/emulator/kernel basics.
- It is support work for phases 4-6 and does not replace RTL/Linux validation gates.

## Workflow

From the `lib/glibc` submodule:

```bash
cd lib/glibc
# run fork-maintained glibc bring-up scripts/workflow
```

Artifacts and logs:

- Artifacts/log locations are defined by the fork workflow.
- Gate artifacts should include `libc.so` and startup objects (`crt*.o`) for Linx target.

## Current gates

- `G1`: configure + build glibc gate targets (`csu/subdir_lib`, `csu/crt1.o`, `libc.so`).

## Exit criteria

- `G1` passes on the reference bring-up host/toolchain.
- Toolchain/libc no longer blocks Linux shell/userland gates.
- Remaining issues are tracked explicitly in `docs/bringup/libc_status.md`.
