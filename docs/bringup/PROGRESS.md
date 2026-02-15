# Bring-up Progress (v0.4 workspace)

Last updated: 2026-02-15

## Phase status

| Phase | Status | Evidence |
| --- | --- | --- |
| 1. Contract freeze (26 checks) | ✅ Passed | `python3 tools/bringup/check26_contract.py --root .` |
| 2. linxisa v0.3 cutover | ✅ Passed | `bash tools/regression/run.sh` |
| 3. LLVM MC/CodeGen alignment | ✅ Passed | `llvm-lit llvm/test/MC/LinxISA llvm/test/CodeGen/LinxISA` |
| 4. QEMU runtime/system alignment | ✅ Passed | `avs/qemu/check_system_strict.sh`; `avs/qemu/run_tests.sh --all` |
| 5. Linux userspace boot path | ✅ Passed | linux initramfs smoke/full/virtio scripts |
| 6. pyCircuit + Janus model alignment | ✅ Bring-up scope complete | pyCircuit/Janus run scripts |
| 7. Skills/docs sync + full stack regression | ✅ Passed | `bash tools/regression/full_stack.sh` |

## Gate snapshot

| Gate | Status | Command |
| --- | --- | --- |
| AVS compile-only (`linx64`/`linx32`) | ✅ | `./avs/compiler/linx-llvm/tests/run.sh` |
| AVS runtime suites | ✅ | `./avs/qemu/run_tests.sh --all` |
| Strict system gate | ✅ | `./avs/qemu/check_system_strict.sh` |
| Main regression | ✅ | `bash tools/regression/run.sh` |
| Full-stack regression | ✅ | `bash tools/regression/full_stack.sh` |

## Latest command log

- `bash tools/regression/run.sh` ✅
- `bash tools/regression/full_stack.sh` ✅
- `python3 tools/isa/check_no_legacy_v03.py --root . --extra-root ~/qemu --extra-root ~/linux --extra-root ~/llvm-project` ✅
- `python3 tools/bringup/check26_contract.py --root .` ✅
