# Linx libc Submodules

The `lib/` workspace hosts LinxISA libc fork mirrors used for Linx Linux bring-up:

- `lib/glibc` -> `git@github.com:LinxISA/glibc.git`
- `lib/musl` -> `git@github.com:LinxISA/musl.git`

Pinned revisions in this tree:

- glibc: `b87a5e30608a7e00aadef9eee035a32ee0611dbf`
- musl: `e1d149303fa91eedcc2beeeb1544502ec7c7b4b3`

## Fresh checkout

```bash
git clone --recurse-submodules git@github.com:LinxISA/linx-isa.git
cd linx-isa
git submodule update --init --recursive
```

## Updating local submodules to pinned commits

```bash
git submodule sync --recursive
git submodule update --init --recursive lib/glibc lib/musl
```

## Applying Linx bring-up patch stacks

Use the top-level make targets so patch application and build logs are consistent:

```bash
make libc-patch-glibc
make libc-patch-musl
make libc-build
```

Artifacts are written under `out/libc/`.
