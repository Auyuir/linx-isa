# Linx libc Bring-up Status

The canonical libc sources are the forked submodules:

- `lib/glibc`
- `lib/musl`

## Repositories and pins

- `lib/glibc` @ `b87a5e30608a7e00aadef9eee035a32ee0611dbf`
- `lib/musl` @ `e1d149303fa91eedcc2beeeb1544502ec7c7b4b3`

## Current policy

- Bring-up changes are maintained in the respective fork history (`LinxISA/glibc`, `LinxISA/musl`).
- This workspace only pins submodule SHAs and documents status.
- Any helper scripts belong in the fork repos, not under `tools/`.

## Latest observed blockers (2026-02-15)

- glibc `G1`: configure fails with `working alias attribute support required` for current Linx clang backend.
- musl `M1`: pass.
- musl `M2`: blocked by Linx clang backend crashes (latest in `src/misc/nftw.c` after locale workarounds).
