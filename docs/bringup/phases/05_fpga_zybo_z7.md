# Phase 5: FPGA Platform Bring-up (Xilinx ZYBO Z7-20)

Target board: Digilent ZYBO Z7-20 (Zynq-7000)

## Objective

Bring Linx CPU first, then Janus Core, onto a stable Zynq PS/PL platform using PS DDR + AXI + PL core integration.

## Platform baseline

- SoC integration path: **PS DDR + AXI + PL core**
- Core is instantiated in PL.
- Linux/test images and staging buffers reside in PS DDR.
- UART and pass/fail MMIO behavior must remain compatible with
  `docs/bringup/contracts/fpga_platform_contract.md`.

## Hardware architecture assumptions

- Deterministic reset sequencing across PS and PL.
- Single bring-up clock domain first; multi-clock extensions are staged later.
- UART console available as primary bring-up visibility channel.
- AXI master bridge in PL for DDR access.

## Bring-up ladder

1. Minimal Linx PL wrapper:
   - core + BRAM/bootstrap path + UART + timer + AXI to PS DDR
2. Board integration:
   - clock/reset wiring, constraints, and reproducible project build
3. Hardware smoke tests:
   - ROM/DDR payload execution with UART pass/fail protocol
4. Janus port:
   - same wrapper pattern and smoke protocol on Janus Core

## Required smoke scenarios

- UART hello and deterministic boot log
- Memory write/readback sanity
- Branch/call control-flow sanity
- MMIO pass/fail register writes

## Exit criteria

- Linx and Janus both run smoke payloads on ZYBO Z7-20.
- Results are reproducible across repeated power cycles.
- Failures are triaged using the same trace/event conventions as simulation.
