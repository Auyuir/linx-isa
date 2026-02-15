#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

fail=0

must_not_exist=(
  "spec"
  "compiler/linx-llvm"
  "emulator/linx-qemu"
  "examples"
  "models"
  "toolchain"
  "tests"
  "docs/validation/avs"
  "tools/ctuning"
  "tools/libc"
  "tools/glibc"
  "workloads/benchmarks"
  "workloads/examples"
  "~"
)

for p in "${must_not_exist[@]}"; do
  if [[ -e "$p" ]]; then
    echo "error: removed path still exists: $p" >&2
    fail=1
  fi
done

if [[ ! -d avs || -L avs ]]; then
  echo "error: avs must be a real directory (not symlink)" >&2
  fail=1
fi

if [[ ! -d isa || -L isa ]]; then
  echo "error: isa must be a real directory (not symlink)" >&2
  fail=1
fi

# Domain-submodule-only checks
if [[ -d compiler ]]; then
  extra="$(find compiler -mindepth 1 -maxdepth 1 -not -name llvm -print -quit)"
  if [[ -n "$extra" ]]; then
    echo "error: compiler/ must contain only compiler/llvm (found: $extra)" >&2
    fail=1
  fi
fi

if [[ -d emulator ]]; then
  extra="$(find emulator -mindepth 1 -maxdepth 1 -not -name qemu -print -quit)"
  if [[ -n "$extra" ]]; then
    echo "error: emulator/ must contain only emulator/qemu (found: $extra)" >&2
    fail=1
  fi
fi

if [[ -d rtl ]]; then
  extra="$(find rtl -mindepth 1 -maxdepth 1 -not -name LinxCore -not -name README.md -print -quit)"
  if [[ -n "$extra" ]]; then
    echo "error: rtl/ contains unexpected entries: $extra" >&2
    fail=1
  fi
  if [[ ! -d rtl/LinxCore ]]; then
    echo "error: missing rtl/LinxCore submodule" >&2
    fail=1
  fi
fi

expected_submodules=(
  "compiler/llvm"
  "emulator/qemu"
  "kernel/linux"
  "rtl/LinxCore"
  "tools/pyCircuit"
  "lib/glibc"
  "lib/musl"
)
for p in "${expected_submodules[@]}"; do
  if ! git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}' | grep -qx "$p"; then
    echo "error: missing submodule path in .gitmodules: $p" >&2
    fail=1
  fi
done

if [[ "$fail" -ne 0 ]]; then
  exit 1
fi

echo "OK: repository layout policy passed"
