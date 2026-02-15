# Linx-AVS (Architecture Validation Suite)

This folder is the canonical Architecture Validation Suite for LinxISA.

Current surfaces in this workspace:

- compile-only suites: `avs/compiler/linx-llvm/tests/`
- runtime suites: `avs/qemu/`
- matrix + machine-readable map: `avs/matrix_v1.md`, `avs/linx_avs_v1_test_matrix.yaml`

## How to use

- Treat `avs/matrix_v1.md` as the normative test matrix.
- Implement runtime-directed tests under `avs/qemu/tests/`.
- Implement compile-only coverage under `avs/compiler/linx-llvm/tests/`.
