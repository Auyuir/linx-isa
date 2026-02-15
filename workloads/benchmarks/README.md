# Benchmarks

This directory keeps benchmark sources close to upstream and provides explicit cross-target runners.

Included suites:

- `coremark/upstream/` — CoreMark upstream sources
- `dhrystone/upstream/` — Dhrystone upstream sources
- `third_party/PolyBenchC/` — fetched on demand
- `ctuning/` — Milepost codelet runner

## Fetch third-party suites

```bash
bash workloads/benchmarks/fetch_third_party.sh
```

## CoreMark + Dhrystone

Build only:

```bash
python3 workloads/benchmarks/run_benchmarks.py \
  --cc /path/to/clang \
  --target <triple>
```

Build + execute through a wrapper (example):

```bash
python3 workloads/benchmarks/run_benchmarks.py \
  --cc /path/to/clang \
  --target <triple> \
  --run-command "qemu-system-linx64 -M virt -nographic -monitor none -kernel {exe}"
```

## PolyBench

```bash
python3 workloads/benchmarks/run_polybench.py \
  --cc /path/to/clang \
  --target <triple> \
  --kernels gemm,jacobi-2d
```

## ctuning Milepost codelets

```bash
python3 workloads/benchmarks/ctuning/run_milepost_codelets.py \
  --ctuning-root ~/ctuning-programs \
  --clang /path/to/clang \
  --lld /path/to/ld.lld \
  --target <triple> \
  --compile-only
```

## Portfolio runner

```bash
python3 workloads/benchmarks/run_portfolio.py --cc /path/to/clang --target <triple>
```
