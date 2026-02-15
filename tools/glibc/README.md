# Legacy glibc path

The active libc bring-up flow is now under `tools/libc/`.

Compatibility items in this folder are kept so older local scripts still resolve:

- `bringup_linx64.sh` -> wrapper that calls `tools/libc/build-glibc.sh`
- `patches/` -> historical patch location

Use the new top-level targets for reproducible bring-up:

```bash
make libc-patch-glibc
make libc-build-glibc
```
