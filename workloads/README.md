# Workloads

Unified home for runnable workload content:

- `benchmarks/` - benchmark suites and runner scripts.
- `generated/` - generated artifacts from workload runs.

## Primary runners

Build CoreMark + Dhrystone (explicit cross target):

```bash
python3 workloads/benchmarks/run_benchmarks.py --cc /path/to/clang --target <triple>
```

Build PolyBench kernels (explicit cross target):

```bash
python3 workloads/benchmarks/run_polybench.py --cc /path/to/clang --target <triple> --kernels gemm,jacobi-2d
```

Run consolidated portfolio:

```bash
python3 workloads/benchmarks/run_portfolio.py --cc /path/to/clang --target <triple>
```
