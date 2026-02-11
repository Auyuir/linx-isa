# Bring-up Progress (strict v0.3)

Last updated: 2026-02-11

## Phase status

| Phase | Status | Evidence |
| --- | --- | --- |
| 1. Contract freeze (26 checks) | ✅ Passed | `python3 tools/bringup/check26_contract.py --root .` |
| 2. linxisa v0.3 cutover | ✅ Passed | `bash tools/regression/run.sh` |
| 3. LLVM MC/CodeGen alignment | ✅ Passed | `llvm-lit llvm/test/MC/LinxISA llvm/test/CodeGen/LinxISA` |
| 4. QEMU runtime/system alignment | ✅ Passed | `tests/qemu/check_system_strict.sh`; `tests/qemu/run_tests.sh --all`; PTO tile suite via `run_pto_ai_kernels.py` |
| 5. Linux userspace boot path | ✅ Passed | `smoke.py`, `full_boot.py`, `virtio_disk_smoke.py` |
| 6. pyCircuit + Janus model alignment | ✅ Passed (bring-up scope) | `run_linx_cpu_pyc_cpp.sh`; `run_janus_bcc_pyc_cpp.sh`; `run_janus_bcc_ooo_pyc_cpp.sh`; `run_linx_qemu_vs_pyc.sh` |
| 7. Skills/docs sync + full stack regression | 🟡 In progress | skills updated in this step; final repo pushes remain pending |

## Gate snapshot

| Gate | Status | Command |
| --- | --- | --- |
| A1 Linx pyCircuit C++ | ✅ | `bash /Users/zhoubot/pyCircuit/tools/run_linx_cpu_pyc_cpp.sh` |
| A3 Linx trace diff | ✅ | `QEMU_BIN=/Users/zhoubot/qemu/build-tci/qemu-system-linx64 bash /Users/zhoubot/pyCircuit/tools/run_linx_qemu_vs_pyc.sh` |
| B1 Janus C++ | ✅ | `bash /Users/zhoubot/pyCircuit/janus/tools/run_janus_bcc_pyc_cpp.sh` |
| B3 Janus/Linx trace compatibility (bring-up subset) | ✅ | same trace diff gate (commit-schema compatible subset) |
| Linux userspace boot | ✅ | linux initramfs smoke/full/virtio scripts |
| PTO GEMM/Flash value match | ✅ | `python3 workloads/benchmarks/compare_pto_cpu_qemu.py` |

## Latest command log

- `bash tools/regression/run.sh` ✅
- `python3 tools/isa/check_no_legacy_v03.py --root . --extra-root /Users/zhoubot/qemu --extra-root /Users/zhoubot/linux --extra-root /Users/zhoubot/llvm-project` ✅
- `python3 workloads/benchmarks/run_pto_ai_kernels.py` ✅
- `python3 workloads/benchmarks/compare_pto_cpu_qemu.py` ✅
- `python3 /Users/zhoubot/linux/tools/linxisa/initramfs/smoke.py` ✅
- `python3 /Users/zhoubot/linux/tools/linxisa/initramfs/full_boot.py` ✅
- `python3 /Users/zhoubot/linux/tools/linxisa/initramfs/virtio_disk_smoke.py` ✅
- `/Users/zhoubot/llvm-project/build-linxisa-clang/bin/llvm-lit -sv /Users/zhoubot/llvm-project/llvm/test/MC/LinxISA /Users/zhoubot/llvm-project/llvm/test/CodeGen/LinxISA` ✅
