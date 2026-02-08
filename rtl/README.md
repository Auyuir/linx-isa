# RTL (bring-up notes)

This directory is the home for the LinxISA RTL implementation and verification collateral.

Bring-up plan (canonical): `docs/bringup/phases/04_rtl.md`
Downstream FPGA phase: `docs/bringup/phases/05_fpga_zybo_z7.md`
Downstream Linux phase: `docs/bringup/phases/06_linux_on_janus.md`

RTL generation flow: pyCircuit repo at `/Users/zhoubot/pyCircuit` (agile bring-up; generates Verilog + C++ cycle models).
Artifact contract: `docs/bringup/contracts/pyc_artifact_contract.md`
Trace contract: `docs/bringup/contracts/trace_schema.md`

## Architectural invariants (do not violate)

Linx uses a block-structured control-flow contract (see `docs/architecture/isa-manual/`):

- **Safety rule:** every architectural control-flow target MUST land on a *block start marker* (`BSTART.*`, `C.BSTART.*`,
  `HL.BSTART.*`, or standalone template blocks like `FENTRY`/`FRET.*`). Targeting a non-marker is an illegal
  instruction / exception.
- **Block boundaries:** a block ends at `BSTOP`/`C.BSTOP` or implicitly at the next block start marker.
- **CARG lifetime:** `SETC.*` updates block-local commit arguments and must execute inside a block; CARG is evaluated at
  block commit and must be preserved across context switches.
- **Template blocks:** `FENTRY`/`FEXIT`/`FRET.*` are standalone blocks (treat them as block start markers for bring-up
  tooling and difftest).

## Spec-driven decode

Decode constants and instruction field definitions should be derived from the canonical catalog:

- `isa/golden/v0.1/` (authoritative sources) and `isa/spec/current/linxisa-v0.1.json` (compiled catalog)
- `isa/generated/codecs/` (generated decode/encode tables)

The intended flow is: `isa/golden/v0.1/* → isa/spec/current/*.json → tools/isa/gen_* → emulator/compiler/RTL`.

## Verification

Recommended early loop:

1. Implement one feature (one instruction, one CSR, one trap).
2. Add a directed test (see `tests/qemu/` and `compiler/llvm/tests/` patterns).
3. Compare commit traces against the emulator (QEMU) on the first-diff divergence.
