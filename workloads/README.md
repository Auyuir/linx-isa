# Workloads

Unified home for runnable workload content:

- `benchmarks/` - benchmark suites and runner scripts.
- `examples/` - standalone example programs.
- `generated/` - generated artifacts from workload runs (objdump, binaries, logs, reports).

Run benchmark workloads:

```bash
python3 workloads/benchmarks/run_benchmarks.py
```

Primary codegen-quality artifacts:

- `workloads/generated/objdump/`
- `workloads/generated/report.md`
