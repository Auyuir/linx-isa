# Phase 8: Toolchain/musl Bring-up

Canonical source repository:

- `lib/musl` (`git@github.com:LinxISA/musl.git`)

## Objective

Bootstrap musl support for `linx64-unknown-linux-musl` with incremental compile gates in the forked musl repository.

## Role in the bring-up sequence

- Musl provides a second libc path for toolchain validation and static userspace experiments.
- This is a bring-up/diagnostic track and does not replace glibc for Linux userspace parity.

## Workflow

From repo root:

```bash
cd lib/musl
# run fork-maintained musl bring-up scripts/workflow
```

Artifacts and logs:

- Artifacts/log locations are defined by the fork workflow.
- Gate artifact should include static libc archive (`libc.a`).

## Current gates

- `M1`: `configure` accepts `linx64-unknown-linux-musl`.
- `M2`: static libc archive `lib/libc.a` builds.
- `M3`: shared libc build is attempted and reported as pass/blocker.

`M3` is non-fatal for now. A blocker is recorded in `out/libc/musl/logs/summary.txt`.

Current Linx backend note:

- `arch/linx64/arch.mak` includes temporary exclusions for `catopen`/`dcngettext` objects because of backend crashes while bringing up `M2`.

## Exit criteria

- `M1` and `M2` pass reliably.
- `M3` is either passing or has an explicit, bounded blocker with owner/action.
- Status remains tracked in `docs/bringup/libc_status.md`.
