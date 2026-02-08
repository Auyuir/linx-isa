# Phase 6: Linux Bring-up on FPGA (Janus End Goal)

Final goal: Linux + BusyBox shell on **Janus Core** running on ZYBO Z7-20 over UART.

## Objective

Use staged Linux bring-up:

1. Linx on FPGA (NOMMU milestone)
2. Janus on FPGA (NOMMU milestone)
3. Janus on FPGA (MMU Linux milestone, final)

## Stage D1: Linx NOMMU Linux

### Entry criteria

- Phase 5 Linx FPGA smoke tests pass.
- Kernel, rootfs/initramfs, and boot image flow are reproducible.

### Acceptance

- Kernel reaches BusyBox shell on UART.
- Smoke commands pass (at minimum): `uname -a` and memory/cpuinfo sanity.

## Stage D2: Janus NOMMU Linux

### Entry criteria

- D1 complete and reproducible.
- Janus FPGA smoke tests pass.

### Acceptance

- Janus reaches BusyBox shell on UART with the same smoke commands.
- Boot path and payload generation are scriptable and repeatable.

## Stage D3: Janus MMU Linux (final)

### Entry criteria

- D2 complete.
- MMU/TLB/page-walk implementation and exception behavior meet architecture requirements.

### Acceptance (final gate)

- Full MMU Linux boots on Janus to BusyBox shell.
- Boot is stable across repeated runs/power cycles.
- Known unsupported features are tracked explicitly with owners.

## Regression requirements

- Keep a minimal Linux boot regression script and log capture process.
- Store gate results and blockers in `docs/bringup/PROGRESS.md` (D1/D2/D3 rows).
