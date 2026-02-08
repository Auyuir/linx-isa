# pyCircuit Artifact Contract

## Authority and source roots

- pyCircuit repository (authoritative): `/Users/zhoubot/pyCircuit`
- Linx CPU source root: `/Users/zhoubot/pyCircuit/examples/linx_cpu_pyc`
- Janus source root: `/Users/zhoubot/pyCircuit/janus/pyc/janus`

`linxisa` does not manually author these RTL/model sources.

## Required generated outputs

For each tracked core target:

- Verilog RTL: `*.v`
- C++ cycle model headers: `*_gen.hpp`
- Testbench execution logs (C++ and RTL simulation paths)

Recommended generated locations in pyCircuit:

- Linx: `/Users/zhoubot/pyCircuit/examples/generated/linx_cpu_pyc/`
- Janus: `/Users/zhoubot/pyCircuit/janus/generated/`

## Canonical generation entrypoints

- `bash /Users/zhoubot/pyCircuit/scripts/pyc build`
- `bash /Users/zhoubot/pyCircuit/scripts/pyc regen`
- `bash /Users/zhoubot/pyCircuit/janus/update_generated.sh`

## Reproducibility rules

- Generated artifacts copied/staged into `linxisa` must come from scripts, not manual edits.
- Every bring-up gate must record the command used and artifact origin.
- If generator versions change, note the version/commit in gate notes.
