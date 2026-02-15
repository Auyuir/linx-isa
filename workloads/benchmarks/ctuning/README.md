# ctuning (Milepost codelets) bring-up runner

This repo uses a **bare-metal** Linx64/Linx32 runtime in QEMU (`-machine virt -kernel <ET_REL.o>`). Most of
`~/ctuning-programs` assumes a hosted environment (filesystem, argv/env, libc, libm).

To get practical coverage quickly, this runner targets the **Milepost codelets** under
`~/ctuning-programs/program/milepost-codelet-*`:

- builds each codelet + wrapper using the Linx LLVM toolchain
- embeds `codelet.data` into the image (no filesystem required)
- runs it under `qemu-system-linx64`

## Usage

```sh
python3 workloads/benchmarks/ctuning/run_milepost_codelets.py --target <triple> --run
```

Common options:

- `--ctuning-root ~/ctuning-programs`
- `--clang ~/llvm-project/build-linxisa-clang/bin/clang`
- `--lld ~/llvm-project/build-linxisa-clang/bin/ld.lld`
- `--qemu ~/qemu/build-tci/qemu-system-linx64`
- `--filter <regex>` to select a subset
- `--compile-only` to only build
