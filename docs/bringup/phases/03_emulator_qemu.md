# Phase 3: Emulator (QEMU) Bring-up

QEMU integration is in sibling repo `~/qemu` (`linx64-softmmu`, machine type `virt`).

## Basic flow

1. Compile C to Linx relocatable object (`.o`, ET_REL)
2. Run with `qemu-system-linx64 -machine virt -kernel <obj.o>`
3. Validate output and exit status

## Test entrypoints

```bash
# Default suites
./tests/qemu/run_tests.sh

# Full suites
./tests/qemu/run_tests.sh --all --timeout 20
```

## Conventions

- UART MMIO base: `0x10000000`
- Exit MMIO: `0x10000004`
- Exit value written at `0x10000004` is used as QEMU process exit code
