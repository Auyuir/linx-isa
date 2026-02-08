# Trace Schema Contract

All differential validation paths must emit a common architectural trace schema.

## Mandatory fields per commit/event

- `cycle`
- `pc`
- `insn`
- `wb_valid`
- `wb_rd`
- `wb_data`
- `mem_valid`
- `mem_addr`
- `mem_wdata`
- `mem_rdata`
- `mem_size`
- `trap_valid`
- `trap_cause`
- `next_pc`

## Producers required to conform

- QEMU reference execution
- pyCircuit C++ cycle model
- RTL simulation (Icarus/Verilator/VCS)
- FPGA reduced trace logger

## Comparison rules

- Compare traces in commit order using identical program image and boot PC.
- First mismatch is the triage anchor; do not skip ahead.
- If a field is unsupported in a path, mark it explicitly and treat as out-of-scope for that gate.

## Gate requirement

No gate can be marked `Passed` if unresolved schema-level divergence remains within the declared instruction subset.
