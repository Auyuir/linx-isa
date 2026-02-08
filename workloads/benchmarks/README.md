# Benchmarks (CoreMark + Dhrystone) for LinxISA QEMU

This folder vendors two classic C benchmarks and provides a small build/run
harness for the LinxISA QEMU `virt` machine.

Benchmarks:

- `coremark/` — EEMBC CoreMark (upstream in `coremark/upstream/`)
- `dhrystone/` — Dhrystone 2.1 (Netlib `dhry-c`, upstream in `dhrystone/upstream/`)

Port notes:

- CoreMark uses a minimal `core_portme.*` under `coremark/linx/`.
- CoreMark builds `core_list_join.c` at `-O0` (the Linx LLVM backend currently
  miscompiles the list-reversal path at `-O2`, breaking CRC validation).
- Dhrystone is adapted for a freestanding environment under `dhrystone/linx/`
  (no `scanf`, no OS timing, no `%f` printing).

Build + run everything and write `workloads/generated/report.md`:

```bash
python3 workloads/benchmarks/run_benchmarks.py
```

Override tool paths:

```bash
export CLANG=~/llvm-project/build-linxisa-clang/bin/clang
export LLD=~/llvm-project/build-linxisa-clang/bin/ld.lld
export QEMU=~/qemu/build/qemu-system-linx64   # or: ~/qemu/build-tci/qemu-system-linx64
python3 workloads/benchmarks/run_benchmarks.py
```

Generated artifacts are written under:

- `workloads/generated/elf/`
- `workloads/generated/bin/`
- `workloads/generated/objdump/` (codegen-quality inspection)
- `workloads/generated/qemu/`
- `workloads/generated/report.md` (static/dynamic instruction counts and histograms)
