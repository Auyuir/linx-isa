# Linx libc Bring-up Status

This file tracks current glibc/musl bring-up state from the reproducible flow under `tools/libc/`.

## Repositories and pins

- `lib/glibc` @ `b87a5e30608a7e00aadef9eee035a32ee0611dbf`
- `lib/musl` @ `e1d149303fa91eedcc2beeeb1544502ec7c7b4b3`

## glibc (`linx64-unknown-linux-gnu`)

- Patch stack:
  - `tools/libc/patches/glibc/0001-glibc-linx-machine-triplet.patch`
  - `tools/libc/patches/glibc/0002-glibc-linx-sysdeps-bootstrap.patch`
- Build script: `tools/libc/build-glibc.sh`
- Gate: `G1`
  - requires `out/libc/glibc/install/lib/libc.so`
  - requires `out/libc/glibc/install/lib/crt1.o`

## musl (`linx64-unknown-linux-musl`)

- Patch stack:
  - `tools/libc/patches/musl/0001-musl-linx64-bootstrap.patch`
- Build script: `tools/libc/build-musl.sh`
- Gates:
  - `M1`: configure accepts Linx target
  - `M2`: `lib/libc.a` built
  - `M3`: shared libc build attempt (non-fatal if blocked)

## Runtime and integration notes

- Both build scripts emit detailed logs into `out/libc/*/logs/`.
- `build-glibc.sh` forces `-fuse-ld=lld` to avoid host linker flag incompatibilities.
- `build-musl.sh` currently uses a bootstrap syscall fallback (`-ENOSYS`) in `arch/linx64/syscall_arch.h` until the final Linux syscall trap ABI is fixed.
- `arch/linx64/arch.mak` temporarily excludes `catopen`/`dcngettext` locale objects due current LLVM backend crashes.

## Latest observed blockers (2026-02-15)

- glibc `G1`: configure fails with `working alias attribute support required` for current Linx clang backend.
- musl `M1`: pass.
- musl `M2`: blocked by Linx clang backend crashes (latest in `src/misc/nftw.c` after locale workarounds).
