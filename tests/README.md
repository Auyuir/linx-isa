# Tests

Unified test surfaces:

- `tests/qemu/`
  - Runtime regression tests executed on Linx QEMU (`run_tests.sh` / `run_tests.py`).
- `tests/scratch/`
  - Ad hoc bring-up and exploratory tests.

Recommended CI/runtime entrypoint:

```bash
bash tools/regression/run.sh
```
