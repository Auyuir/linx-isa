# Linx ISA Bring-up: Detailed Technical Checklist

**Source Document:** `linx-bingup.md`  
**Version:** 1.0  
**Date:** 2026-02-11  
**Purpose:** Comprehensive technical checklist for implementing, verifying, and maintaining LinxISA across all components (spec, compiler, QEMU, RTL, Linux)

---

## Quick start (strict v0.3 current)

Run the full cross-stack bring-up regression (spec/gates + LLVM + QEMU + Linux boot + PTO value match + pyCircuit/Janus):

```bash
bash /Users/zhoubot/linxisa/tools/regression/full_stack.sh
```

Normative contract and ownership:

- Strict 26-check contract (machine-checkable): `docs/bringup/check26_contract.yaml`
- Contract gate: `python3 /Users/zhoubot/linxisa/tools/bringup/check26_contract.py --root /Users/zhoubot/linxisa`
- Strict v0.3 canonical-output denylist: `python3 /Users/zhoubot/linxisa/tools/isa/check_no_legacy_v03.py --root /Users/zhoubot/linxisa --extra-root /Users/zhoubot/qemu --extra-root /Users/zhoubot/linux --extra-root /Users/zhoubot/llvm-project`

Terminology notes (strict v0.3):

- Template restore is `ERCOV` (some older texts use `ERET`; treat `ERET` as a synonym of `ERCOV`, but canonical artifacts must say `ERCOV`).
- Canonical v0.3 disassembly uses typed `BSTART.*`; `BSTART.PAR` is compatibility input only.
- Canonical v0.3 vector mnemonics are `V.*`; legacy `L.*` spellings are compatibility input only.

## Evidence (per-check)

This checklist is intentionally detailed and human-oriented. For machine-checkable ownership and required evidence per
check, use the strict contract ledger:

- `docs/bringup/check26_contract.yaml` → `checks[]` entries contain `owners[]` and `tests[]`.

## Table of Contents

1. [Check 1: Block-Structured ISA Foundation](#check-1-block-structured-isa-foundation)
2. [Check 2: Global State (GSTATE) Architecture](#check-2-global-state-gstate-architecture)
3. [Check 3: Local Block State (BSTATE) Hierarchy](#check-3-local-block-state-bstate-hierarchy)
4. [Check 4: ESAVE/ERCOV Template Blocks](#check-4-esaveercov-template-blocks)
5. [Check 5: Hierarchical Machine Model (BCC + PEs)](#check-5-hierarchical-machine-model-bcc--pes)
6. [Check 6: Block-Based Computation Organization](#check-6-block-based-computation-organization)
7. [Check 7: Control Flow and Block Commit](#check-7-control-flow-and-block-commit)
8. [Check 8: Control Flow Safety Rule](#check-8-control-flow-safety-rule)
9. [Check 9: Block Boundary Instructions](#check-9-block-boundary-instructions)
10. [Check 10: Block Attribute Instructions](#check-10-block-attribute-instructions)
11. [Check 11: Block Type Sequential Organization](#check-11-block-type-sequential-organization)
12. [Check 12: Block as Variable-Length CISC](#check-12-block-as-variable-length-cisc)
13. [Check 13: Coupled vs Decoupled Blocks](#check-13-coupled-vs-decoupled-blocks)
14. [Check 14: B.TEXT and Template Blocks](#check-14-btext-and-template-blocks)
15. [Check 15: TEPL Extensibility](#check-15-tepl-extensibility)
16. [Check 16: Floating-Point Support](#check-16-floating-point-support)
17. [Check 17: Vector/SIMT Instructions](#check-17-vectorsimt-instructions)
18. [Check 18: BSTART.MPAR Parallel Execution](#check-18-bstartmpar-parallel-execution)
19. [Check 19: BSTART.VPAR/VSEQ Vector Blocks](#check-19-bstartvparvseq-vector-blocks)
20. [Check 20: Tile Register Architecture](#check-20-tile-register-architecture)
21. [Check 21: Block Command Interface (Layer 1 to Layer 2)](#check-21-block-command-interface-layer-1-to-layer-2)
22. [Check 22: Second Layer PE Execution](#check-22-second-layer-pe-execution)
23. [Check 23: Vector PE Memory Access (TSO Model)](#check-23-vector-pe-memory-access-tso-model)
24. [Check 24: Tile Load/Store TLB/MMU](#check-24-tile-loadstore-tlummu)
25. [Check 25: MSEQ/MPAR via TMA](#check-25-mseqmpar-via-tma)
26. [Check 26: Vector Block Encoding Requirements](#check-26-vector-block-encoding-requirements)

---

## Check 1: Block-Structured ISA Foundation

### 1.1 Core Concept
- [ ] Verify specification defines LinxISA as a **block-structured** (hierarchical) ISA
- [ ] Confirm architectural documentation uses consistent terminology: "block-structured" OR "hierarchical" (not both interchangeably)
- [ ] Ensure all instruction families reference block structure as foundational model

### 1.2 Two-Layer State Model
- [ ] Verify architectural documentation explicitly states: "Linx CPU has two hierarchical sets of architectural states"
- [ ] Check that Layer 1 (GSTATE) and Layer 2 (BSTATE) are clearly delineated
- [ ] Confirm no mixed terminology (e.g., "local state" without specifying BSTATE)

### 1.3 Documentation Verification
| Component | Document | Section | Status |
|-----------|----------|---------|--------|
| ISA Manual | `docs/architecture/isa-manual/` | Block ISA chapter | [ ] |
| JSON Spec | `isa/spec/current/` | State definitions | [ ] |
| Skills | `$CODEX_HOME/skills/` | Architecture skills | [ ] |

---

## Check 2: Global State (GSTATE) Architecture

### 2.1 GPR Definition (R0-R23)
- [ ] Verify 24 GPRs (R0-R23) in JSON spec register table
- [ ] Confirm R0 is zero register (if applicable)
- [ ] Check special registers: ra (return address), sp (stack pointer), gp (global pointer), tp (thread pointer)
- [ ] Verify ABI documentation for register usage conventions

### 2.2 Tile Registers
- [ ] Verify 32 tile registers in spec
- [ ] Confirm minimum size: 512B per tile register
- [ ] Confirm maximum size: 4KB per tile register
- [ ] Check architectural state records tile size for each tile register
- [ ] Verify Tile Register Allocation (TRA) documentation for compiler

### 2.3 SSR (System Status Registers)
- [ ] List all SSRs in architectural specification
- [ ] Verify SSR access control (privileged vs user)
- [ ] Check SSR encoding in instruction set (SSRGET, HL.SSRGET)
- [ ] Document SSR reset values

### 2.4 Verification Checklist
```
□ GPR count: 24 (R0-R23) - CONFIRMED
□ Tile register count: 32 - CONFIRMED  
□ Tile register min size: 512B - CONFIRMED
□ Tile register max size: 4KB - CONFIRMED
□ Total tile register space: 32 × 4KB = 128KB - CONFIRMED
□ SSR list complete - PENDING VERIFICATION
□ SSR encoding documented - PENDING VERIFICATION
```

---

## Check 3: Local Block State (BSTATE) Hierarchy

### 3.1 Scalar Block States
#### T Hand Queue
- [ ] Verify 4-depth queue implementation
- [ ] Document queue semantics: shift on push, kill oldest value
- [ ] Check instruction syntax: `->t`, `t#1`, `t#2`, `t#3`, `t#4`
- [ ] (Non-normative / defer) Optional bring-up simplification: "no more than one T read per instruction"

#### U Hand Queue  
- [ ] Verify 4-depth queue implementation
- [ ] Document queue semantics: shift on push, kill oldest value
- [ ] Check instruction syntax: `->u`, `u#1`, `u#2`, `u#3`, `u#4`
- [ ] (Non-normative / defer) Optional bring-up simplification: "no more than one U read per instruction"

#### BCARG (Block Commit Argument)
- [ ] Document BCARG fields:
  - Block type
  - Current BPC
  - Next BPC
  - SETC conditional flags
- [ ] Verify BCARG reset at block start
- [ ] Confirm BCARG commit semantics at block boundary

### 3.2 Vector Block States
#### VT Hand Queue
- [ ] Verify 4-depth, 64-bit width
- [ ] Document lane semantics (each lane is 32-bit)
- [ ] Check variable lane count support

#### VU Hand Queue
- [ ] Verify 4-depth, 64-bit width
- [ ] Document lane semantics (each lane is 32-bit)
- [ ] Check variable lane count support

#### VM Hand Queue
- [ ] Verify 4-depth, 64-bit width
- [ ] Document mask semantics (per-lane masking)
- [ ] Check predicate integration

#### VN Hand Queue
- [ ] Verify 4-depth, 64-bit width
- [ ] Document lane index semantics
- [ ] Check counter/index support

### 3.3 Template Block States
- [ ] Verify internal FSM states for restartability
- [ ] Document save/restore mechanism
- [ ] Confirm state preservation across traps
- [ ] Check ESAVE/ERCOV integration with template states

### 3.4 BSTATE Verification Matrix
| State Type | Queue Depth | Width | Variable Lanes | Status |
|------------|-------------|-------|----------------|--------|
| T Hand | 4 | 64-bit | N/A | [ ] |
| U Hand | 4 | 64-bit | N/A | [ ] |
| VT Hand | 4 | 64-bit | Yes | [ ] |
| VU Hand | 4 | 64-bit | Yes | [ ] |
| VM Hand | 4 | 64-bit | Yes | [ ] |
| VN Hand | 4 | 64-bit | Yes | [ ] |
| Template FSM | N/A | N/A | N/A | [ ] |

---

## Check 4: ESAVE/ERCOV Template Blocks

### 4.1 ESAVE (Extended Save)
- [ ] Document ESAVE syntax: `ESAVE [BasePtr, LenBytes, Kind]`
- [ ] Verify it saves Layer 2 (BSTATE) to Layer 1 (GSTATE)
- [ ] Confirm BSTATE is a union structure
- [ ] Check Kind parameter encoding
- [ ] Verify restartability semantics

### 4.2 ERCOV (Extended Recover)
- [ ] Document ERCOV syntax: `ERCOV [BasePtr, LenBytes, Kind]`
- [ ] Verify it restores BSTATE from GSTATE
- [ ] Confirm state restoration order
- [ ] Check exception handling during restore

### 4.3 Union Structure Verification
- [ ] Document BSTATE union members
- [ ] Verify scalar state (T/U queues, BCARG)
- [ ] Verify vector state (VT/VM/VN/VU)
- [ ] Verify template internal states
- [ ] Confirm union encoding in save/restore

### 4.4 Implementation Checklist
```
□ ESAVE instruction encoding defined
□ ERCOV instruction encoding defined  
□ BSTATE union structure documented
□ Save/restore state machine verified
□ Restartability contract tested
□ Exception handling verified
```

---

## Check 5: Hierarchical Machine Model (BCC + PEs)

### 5.1 BCC (Block Control Core) Responsibilities
- [ ] Verify BCC is the scheduler for block execution
- [ ] Document block dependency tracking
- [ ] Check block reorder buffer (BROB) implementation
- [ ] Verify in-order commit despite out-of-order execution

### 5.2 Heterogeneous PEs
- [ ] Document PE types:
  - Scalar PE
  - Vector PE
  - Cube PE (systolic array)
  - TAU PE (tensor accelerator)
  - TMA PE (tensor memory accelerator)
- [ ] Verify PE receives block commands from BCC
- [ ] Check PE sends results back to BCC

### 5.3 Shared GSTATE
- [ ] Verify all PEs share:
  - 24 GPRs
  - 32 Tile Registers
  - All SSRs
- [ ] Document PE-specific private state
- [ ] Check GSTATE access synchronization

### 5.4 Machine Model Diagram
```
                    ┌─────────────────┐
                    │    GSTATE       │
                    │  (24 GPRs,     │
                    │   32 Tiles,    │
                    │    SSRs)       │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐
        │ Scalar  │   │ Vector  │   │  Cube   │
        │   PE    │   │   PE    │   │   PE    │
        └────┬────┘   └────┬────┘   └────┬────┘
             │             │             │
             └─────────────┼─────────────┘
                           │
                    ┌──────┴──────┐
                    │     BCC      │
                    │  (Scheduler) │
                    │    BROB      │
                    └─────────────┘
```

---

## Check 6: Block-Based Computation Organization

### 6.1 Block Granularity
- [ ] Verify no instructions exist between blocks
- [ ] Confirm empty blocks are allowed
- [ ] Document block as atomic computation unit

### 6.2 Sequential Block Execution
- [ ] Verify program order: BlockA → BlockB → BlockC
- [ ] Check block boundary markers (BSTART/BSTOP)
- [ ] Document block commit ordering

### 6.3 Compiler Guidelines
- [ ] Verify compiler emits blocks as basic units
- [ ] Check block formation algorithm
- [ ] Document T/U queue usage optimization

### 6.4 Example Block Structure
```assembly
BSTART                    ; Block start marker
add   a0, a1 -> t        ; Compute with T-hand queue
sub   t#1, a2 -> u       ; Use T result, write to U-hand
sw    zero, [u#1, 100]   ; Store output
BSTOP                    ; Block stop/commit
```

---

## Check 7: Control Flow and Block Commit

### 7.1 Block Commit Semantics
- [ ] Verify control flow happens AFTER block commit
- [ ] Document BARG.NextBPC computation during block execution
- [ ] Confirm NextBPC becomes global PC at block boundary

### 7.2 Internal Computation vs Control Flow
- [ ] Verify blocks compute/predict next block address
- [ ] Check BARG.NextBPC update timing
- [ ] Document commit point: BSTOP or next BSTART

### 7.3 Fall-Through Behavior
- [ ] Verify fall-through if no branch target set
- [ ] Document implicit fall-through to next block
- [ ] Check explicit BSTOP for fall-through clarity

---

## Check 8: Control Flow Safety Rule

### 8.1 Mandatory Block Boundary Targets
- [ ] Document rule: ALL control flow MUST jump to block boundaries
- [ ] Verify exception for illegal control flow:
  - Branching to middle of block → IllegalInstruction exception
- [ ] Check exception encoding: `E_INST(EC_ILLEGAL)`

### 8.2 Control Flow Integrity
- [ ] Document purpose: safety and integrity
- [ ] Verify hardware enforcement
- [ ] Check compiler responsibility for valid targets

### 8.3 Valid Block Start Markers
- [ ] BSTART.xxx (all variants)
- [ ] C.BSTART.xxx (compressed)
- [ ] HL.BSTART.xxx (high-level)
- [ ] Template blocks: FENTRY, FEXIT, FRET.*

### 8.4 Safety Rule Verification
```
□ All branch targets verified to be block starts
□ Illegal target detection implemented
□ Exception handling tested
□ Compiler generates valid targets only
```

---

## Check 9: Block Boundary Instructions

### 9.1 BSTART Variants
- [ ] BSTART.STD (standard scalar)
- [ ] BSTART.COND (conditional)
- [ ] BSTART.DIRECT (direct branch)
- [ ] BSTART.CALL (function call)
- [ ] BSTART.RET (return)
- [ ] BSTART.IND (indirect)
- [ ] BSTART.FP (floating-point)
- [ ] BSTART.SYS (system)
- [ ] BSTART.TMA (tensor memory)
- [ ] BSTART.CUBE (systolic array)
- [ ] BSTART.MPAR (parallel)
- [ ] BSTART.MSEQ (sequential vector)
- [ ] BSTART.VPAR (vector parallel)
- [ ] BSTART.VSEQ (vector sequential)
- [ ] BSTART.TEPL (template extension)

### 9.2 Compressed Forms
- [ ] C.BSTART (all variants)
- [ ] C.BSTOP (all-zeros encoding)

### 9.3 BSTOP Semantics
- [ ] Verify BSTOP serves as NOP if jumped to directly
- [ ] Document BSTOP as explicit block terminator
- [ ] Check L.BSTOP (if applicable)

### 9.4 Special Block Boundary Instructions
- [ ] BWE (bus wait event)
- [ ] BWI (bus wait interrupt)
- [ ] ACRE (ACR enter)
- [ ] ACRC (ACR service request)
- [ ] EBREAK (debug breakpoint)

---

## Check 10: Block Attribute Instructions

### 10.1 B.ARG (Block Argument)
- [ ] Document syntax: `B.ARG <immediate>`
- [ ] Verify conveys immediate values at block initialization
- [ ] Check different interpretations per block type
- [ ] Verify header-only semantics

### 10.2 B.ATTR (Block Attribute)
- [ ] Document syntax: `B.ATTR {options}`
- [ ] Verify controls barriers between blocks
- [ ] Check options: trap, atomic, aq, rl, aqrl, far, DataLayout

### 10.3 B.IOR (Block Input/Output Registers)
- [ ] Document syntax: `B.IOR [input_regs], [output_regs]`
- [ ] Verify defines live-in and live-out registers
- [ ] Check: only for decoupled/template blocks
- [ ] Document absolute GPR ID encoding
- [ ] Verify sensitivity list semantics

### 10.4 B.IOT (Block Input/Output Tiles)
- [ ] Document syntax: `B.IOT [input_tiles], -> output_tile`
- [ ] Verify relative register encoding (SSA form)
- [ ] Check: tile output never overrides input tile
- [ ] Verify SSA form semantics
- [ ] Document B.IOT encoding: `B.IOT [T#k, M#j] -> U`

### 10.5 B.IOD (Block Input/Output Dependencies) - DEPRECATED
- [ ] Mark as obsolete
- [ ] Document: was for dummy dependencies between block instructions
- [ ] Verify no new code uses B.IOD

---

## Check 11: Block Type Sequential Organization

### 11.1 Block Type Categories
- [ ] Scalar blocks (normal compute)
- [ ] Template blocks (FENTRY, FEXIT, FRET)
- [ ] Tile blocks (TMA, CUBE, etc.)

### 11.2 Sequential Execution Model
- [ ] Verify LinxCPU executes blocks sequentially in program order
- [ ] Confirm block types do not affect scheduling order
- [ ] Document: scheduling depends ONLY on dependencies

### 11.3 Block Reorder Buffer (BROB)
- [ ] Verify BROB controls block retirement
- [ ] Confirm in-order commit regardless of execution order
- [ ] Check misprediction/exception flushing

### 11.4 Dependency-Based Scheduling
- [ ] Verify blocks issue when inputs ready
- [ ] Check scalar block exception: no wait for inputs ready
- [ ] Document scalar issue queue semantics

---

## Check 12: Block as Variable-Length CISC

### 12.1 Block Instruction Encoding
- [ ] Verify block is variable-length CISC instruction
- [ ] Check encoding lengths: 16-bit, 32-bit, 48-bit, 64-bit
- [ ] Document prefix/postfix composition

### 12.2 Example Block Translation
```assembly
; Block (high-level):
BSTART
add   a0, a1 -> t          ; = t0 = a0 + a1
sub   t#1, a2 -> u         ; u0 = t1 - a2
sw    zero, [u#1, 100]    ; mem[u0 + 100] = 0
BSTOP

; Equivalent CISC:
sw zero, [(a0+a1)-a2, 100]
```

### 12.3 T/U Queue Constraints
- [ ] Verify one producer per queue entry
- [ ] Verify one consumer per queue entry
- [ ] Document: enables hardware internal forwarding
- [ ] Check: simplifies speculative state management

### 12.4 Compiler Guidelines
- [ ] Document: use T/U hands as much as possible
- [ ] Verify compiler optimization for queue usage
- [ ] Check register allocation for block inputs/outputs

---

## Check 13: Coupled vs Decoupled Blocks

### 13.1 Coupled Blocks
- [ ] Verify microinstructions embedded in BSTART/BSTOP form
- [ ] Document: executed in first layer (Scalar PE)
- [ ] Check: all instructions in one block body
- [ ] Verify normal CFG mapping

### 13.2 Decoupled Blocks
- [ ] Verify header and body at different PCs
- [ ] Document: header in first layer, body in second layer
- [ ] Check: B.TEXT required for body pointer

### 13.3 B.TEXT Specification
- [ ] Document syntax: `B.TEXT <body_label>`
- [ ] Verify: only visible in decoupled blocks
- [ ] Check: offset encoding to body location
- [ ] Confirm: not a block boundary

### 13.4 Decoupled Block Structure
```assembly
; Header (in linear stream):
BSTART.TMA
B.IOT [T#0], -> T#1
B.TEXT <.body_tma>
BSTOP

; Body (out-of-line):
.body_tma:
tma.load  T#1 -> T#2
tma.store T#0 <- T#2
BSTOP
```

---

## Check 14: B.TEXT and Template Blocks

### 14.1 B.TEXT Functionality
- [ ] Verify decides if block has separate body
- [ ] Document: assigns offset to body location
- [ ] Check: compiler responsibility for body placement

### 14.2 Template Block Variants
- [ ] FENTRY (function entry)
- [ ] FEXIT (function exit)
- [ ] FRET.RA (return with register save)
- [ ] FRET.STK (return with stack restore)
- [ ] ESAVE (extended save)
- [ ] ERCOV (extended recover)

### 14.3 Template Implementation Strategies
#### Implementation A (ROM-based)
- [ ] Verify body stored in internal ROM
- [ ] Check: static template contents
- [ ] Document: compile-time template selection

#### Implementation B (Code Template FSM)
- [ ] Verify dynamic uop generation by CT FSM
- [ ] Check: microcode-style execution
- [ ] Document: FSM state machine

#### Implementation C (Command Packing)
- [ ] Verify input data packing to commands
- [ ] Check: send to internal engine
- [ ] Document: command/response protocol

---

## Check 15: TEPL Extensibility

### 15.1 TEPL Block Syntax
```assembly
BSTART.TEPL <opcode>
B.ATTR <attributes>
B.ARG <arguments>
B.IOR [input_regs], [output_regs]
B.IOT [input_tiles], -> output_tile
BSTOP
```

### 15.2 TEPL Compiler Interface
- [ ] Document intrinsic syntax:
  ```c
  __linx_block(opc, ins(%r0, ..., %rn, %tile0, ..., %tilen), 
               outs(%r0, ..., %rm, %tile0, ..., %tilem))
  ```
- [ ] Verify generic interface for accelerator PEs
- [ ] Check: PE must NOT touch memory

### 15.3 TEPL Constraints
- [ ] Verify opcode encoding
- [ ] Document attribute encoding
- [ ] Check: no direct memory access by PE

### 15.4 Future Accelerator List
- [ ] Document planned accelerators:
  - [ ] Tensor operations
  - [ ] Cryptographic engines
  - [ ] Signal processing
  - [ ] Network processing

---

## Check 16: Floating-Point Support

### 16.1 FP Architecture
- [ ] Verify NO dedicated FP architectural state
- [ ] Document: integer and FP share Layer 1 state
- [ ] Check: same GPRs for FP values

### 16.2 BSTART.FP Block Type
- [ ] Verify BSTART.FP indicates FP instructions present
- [ ] Document: serves as hint to hardware
- [ ] Check: allows scalar/FP instruction interleaving

### 16.3 FP Instruction Set
- [ ] List FP arithmetic: FADD, FSUB, FMUL, FDIV
- [ ] List FP compare: FEQ, FLT, FLE
- [ ] List FP conversion: FCVT
- [ ] List FP square root: FSQRT

### 16.4 FP Exception Handling
- [ ] Verify v0.2 does NOT deliver FP traps
- [ ] Document: FP operations only update sticky status (FFLAGS)
- [ ] Check: IEEE 754 compliance

---

## Check 17: Vector/SIMT Instructions

### 17.1 Vector Design Philosophy
- [ ] Verify SIMT-style architecture (not AVX/SVE)
- [ ] Document: hardware loop support
- [ ] Check: per-lane execution model

### 17.2 MSEQ Block for Loops
```assembly
BSTART.MSEQ
.TEXT <.body>
B.IOR [s0], []         ; s0 = array base
B.DIM a0 -> lb0        ; a0 = inner loop count (m)
B.DIM a1 -> lb1        ; a1 = outer loop count (n)
BSTOP

.body:
v.add  lc0.sw, lc1.sw -> vt
v.st   vt#1, [ri0, lc0<<2, lc1<<10]
BSTOP
```

### 17.3 Vector Block Components
- [ ] Verify B.IOR for input specification
- [ ] Verify B.DIM for loop dimensions
- [ ] Document: single lane of compute in body
- [ ] Check: hardware unrolls loop

### 17.4 Vector Block Semantics
- [ ] Verify: single lane specification
- [ ] Document: hardware repeats for all lanes
- [ ] Check: in-order loop iteration commit

---

## Check 18: BSTART.MPAR Parallel Execution

### 18.1 MPAR Semantics
```assembly
parallel_for (int i=0; i<n; i++) {
    parallel_for (int j=0; j<m; j++) {
        a[i][j] = i + j;
    }
}
```

### 18.2 PAR vs SEQ Comparison
| Aspect | MSEQ | MPAR |
|--------|------|------|
| Execution | Sequential across VLEN | Parallel across all lanes |
| Commit | Sequential | Parallel (all lanes at once) |
| Memory | Ordered | Ordered within block |
| Synchronization | Implicit | Explicit barriers |

### 18.3 MPAR Block Structure
- [ ] Verify BSTART.MPAR block type
- [ ] Document: parallel commit semantics
- [ ] Check: lane synchronization requirements

### 18.4 Implementation Requirements
- [ ] Verify parallel dispatch
- [ ] Document: parallel result collection
- [ ] Check: exception handling across lanes

---

## Check 19: BSTART.VPAR/VSEQ Vector Blocks

### 19.1 VPAR (Vector Parallel)
- [ ] Document: parallel vector execution
- [ ] Verify: NO memory access
- [ ] Check: tile register only access

### 19.2 VSEQ (Vector Sequential)
- [ ] Document: sequential vector execution
- [ ] Verify: NO memory access
- [ ] Check: tile register only access

### 19.3 VPAR/VSEQ Use Cases
- [ ] Verify: significant performance improvement
- [ ] Document: out-of-order execution across blocks
- [ ] Check: speculative execution support

### 19.4 Tile-Only Constraint
- [ ] Verify VPAR/VSEQ cannot access main memory
- [ ] Document: must use B.IOR for data input/output
- [ ] Check: scalar pipe for memory operations

---

## Check 20: Tile Register Architecture

### 20.1 Tile Register Properties
| Property | Value | Status |
|----------|-------|--------|
| Count | 32 | [ ] |
| Minimum size | 512B | [ ] |
| Maximum size | 4KB | [ ] |
| Total space | 128KB | [ ] |
| Renaming | Supported | [ ] |
| Relative encoding | SSA form | [ ] |

### 20.2 Architectural State
- [ ] Verify: tile size recorded as architectural state
- [ ] Document: each tile has architectural size
- [ ] Check: hardware implementation details

### 20.3 Tile Renaming
- [ ] Verify: more physical tiles than architectural
- [ ] Document: register renaming for performance
- [ ] Check: dependency tracking

### 20.4 Relative Encoding (SSA)
- [ ] Verify B.IOT uses relative encoding
- [ ] Document: SSA form for tile registers
- [ ] Check: Tile input preserved across block

### 20.5 Compiler Challenges
- [ ] Verify: tile allocation is difficult
- [ ] Document: ClockHands for vector blocks
- [ ] Check: SSA distance requirements

---

## Check 21: Block Command Interface (Layer 1 to Layer 2)

### 21.1 Block Command Format
Each block descriptor packs into the block command:

| Descriptor | Packed Information |
|------------|-------------------|
| BSTART.XXX | opcode, block_id, info |
| B.IOR | input register data, output ptag reservation |
| B.IOT | tile rename, input/output addresses |
| B.ARG | immediate values |
| B.ATTR | attribute flags |
| B.IOD | dependency resolution |
| B.DIM | block dimensions |
| B.TEXT | body PC calculation |
| BSTOP | trigger block execution |

### 21.2 BSTART.XXX Packing
- [ ] Verify opcode packing
- [ ] Document block_id encoding
- [ ] Check info field semantics

### 21.3 B.IOR Packing
- [ ] Verify register data read when ready
- [ ] Document output ptag reservation
- [ ] Check: input readiness tracking

### 21.4 B.IOT Packing
- [ ] Verify tile rename operations
- [ ] Document: input/output address calculation
- [ ] Check: command packing

### 21.5 B.TEXT Packing
- [ ] Verify PC calculation
- [ ] Document: offset encoding
- [ ] Check: body PC in command

### 21.6 BSTOP Packing
- [ ] Verify all field readiness check
- [ ] Document: trigger to second layer
- [ ] Check: block command issuance

---

## Check 22: Second Layer PE Execution

### 22.1 PE Activation
- [ ] Verify: PE only active when receiving valid block command
- [ ] Document: buffer and parse block command
- [ ] Check: command interpretation

### 22.2 PE Types and Operations
#### Vector PE
- [ ] Verify: retrieve input data
- [ ] Document: block dim repeat value
- [ ] Check: execution mode and PC jump

#### Cube PE
- [ ] Verify: input tile address (left/right)
- [ ] Document: M, N, K values
- [ ] Check: systolic array uop splitting

#### TAU PE
- [ ] Verify: input tile address
- [ ] Document: opcode
- [ ] Check: tile load into accelerator

#### TMA PE
- [ ] Verify: arguments, layout, stride, range
- [ ] Document: tensor load/store operations
- [ ] Check: global memory access

#### Generic PE
- [ ] Verify: B.IOR interpretation
- [ ] Document: B.IOT interpretation
- [ ] Check: custom opcode handling

### 22.3 Completion Protocol
When block command finishes:
- [ ] Verify: pack live-out into response
- [ ] Document: status (success, fail, exception)
- [ ] Check: BROB update

### 22.4 Multi-Command Support
- [ ] Verify: PE may execute multiple commands
- [ ] Document: command buffering
- [ ] Check: resource management

---

## Check 23: Vector PE Memory Access (TSO Model)

### 23.1 Memory Access Restriction
- [ ] Verify: Vector PE has NO direct memory access
- [ ] Document: only scalar pipe and TMA access memory
- [ ] Check: enforced by architecture

### 23.2 TSO (Total Store Order) Model
- [ ] Verify: store values not reordered
- [ ] Document: per-location coherence guaranteed
- [ ] Check: address independence not guaranteed

### 23.3 Memory Ordering Rules
| Operation | Ordering |
|-----------|----------|
| Scalar load/store | TSO |
| TLOAD/TSTORE | TSO |
| Atomic .aq/.rl | Stronger ordering |
| FENCE.D | Full barrier |
| FENCE.I | Instruction barrier |

### 23.4 Out-of-Order Issue, In-Order Commit
- [ ] Verify: memory operations issue out of order
- [ ] Document: commit in program order
- [ ] Check: TSO enforcement

---

## Check 24: Tile Load/Store TLB/MMU

### 24.1 Unified Memory Hierarchy
- [ ] Verify: scalar and tile access same TLB/MMU
- [ ] Document: single translation lookaside buffer
- [ ] Check: unified page table

### 24.2 Tile Access Semantics
- [ ] Verify: ranged access (2D)
- [ ] Document: may require multiple TLB lookups
- [ ] Check: page fault handling

### 24.3 Restartability Requirement
- [ ] Verify: tile load/store must be restartable
- [ ] Document: OS responsibility for page preparation
- [ ] Check: trap handler requirements

### 24.4 OS Requirements
- [ ] Verify: must prepare TLOAD/TSTORE pages
- [ ] Document: page fault handling for tile ops
- [ ] Check: resume semantics

---

## Check 25: MSEQ/MPAR via TMA

### 25.1 Memory Access Pipeline
For MSEQ/MPAR blocks accessing global memory:

```
Step 1: Write DDR address to tile register
Step 2: Notify TMA
Step 3: TMA reads tile register, gets DDR address
Step 4: TMA performs load
Step 5: Load data returns to tile register
Step 6: Vector core reads tile register
```

### 25.2 TMA Integration
- [ ] Verify: TMA as memory bridge
- [ ] Document: tile register → DDR address translation
- [ ] Check: data return path

### 25.3 Memory Barriers
- [ ] Verify: barriers between MSEQ/MPAR blocks
- [ ] Document: avoid memory conflicts
- [ ] Check: barrier instruction encoding

### 25.4 Synchronization Points
- [ ] Verify: TMA completion notification
- [ ] Document: vector core ready signal
- [ ] Check: error propagation

---

## Check 26: Vector Block Encoding Requirements

### 26.1 Local vs Global Access Encoding
| Access Type | Syntax | Encoding Bit |
|-------------|--------|--------------|
| Local (tile) | `lw.local [ri0, vt#1] -> vt` | [ ] |
| Global (bridge) | `lw.brg [addr]` | [ ] |

### 26.2 B.IOR Mapping for Vector
- [ ] Verify: ri0, ri1, ..., rin map B.IOR ordered arguments
- [ ] Document: input register access
- [ ] Check: output register access

### 26.3 Tile Reference Naming
- [ ] Verify: TA, TB for input bases
- [ ] Document: TO for output base
- [ ] Check: TS for scratch base

### 26.4 Mixed Scalar/Vector Instructions
- [ ] Verify: scalar and vector instructions can mix
- [ ] Document: scalar uses (t, u, p)
- [ ] Check: vector uses (vt, vu, vm, vn, p)

### 26.5 Vector Groups (SIMT Warps)
- [ ] Verify: group-level instructions
- [ ] Document: inter-group instructions
- [ ] Check: warp-like semantics

### 26.6 Complete Vector Block Example
```assembly
BSTART.VPAR
.TEXT <.vec_body>
B.IOR [s0, s1], [s2]       ; s0=baseA, s1=baseB, s2=result
B.IOT [T#0], -> T#1          ; T#0=input, T#1=output
BSTOP

.vec_body:
lw.local [ri0, vt#1] -> vt   ; local tile load
v.add  vt#1, vt#2 -> vt#3    ; vector add
v.mul  vt#3, vt#4 -> vt#5    ; vector multiply
st.local vt#5, [ri0, vt#1]   ; local tile store
BSTOP
```

---

## Appendix A: Cross-Component Verification Matrix

| Check | ISA Manual | JSON Spec | LLVM | QEMU | RTL |
|-------|-------------|-----------|------|------|-----|
| 1 | [ ] | [ ] | N/A | [ ] | [ ] |
| 2 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 5 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 6 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 7 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 8 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 9 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 10 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 11 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 12 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 13 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 14 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 15 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 16 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 17 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 18 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 19 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 20 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 21 | [ ] | [ ] | N/A | [ ] | [ ] |
| 22 | [ ] | [ ] | N/A | [ ] | [ ] |
| 23 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 24 | [ ] | [ ] | N/A | [ ] | [ ] |
| 25 | [ ] | [ ] | [ ] | [ ] | [ ] |
| 26 | [ ] | [ ] | [ ] | [ ] | [ ] |

---

## Appendix B: Skill References

| Skill Module | Path | Purpose |
|--------------|------|---------|
| Architecture | `linx-skills/linx-arch-bringup/` | Block ISA decisions |
| LLVM | `linx-skills/linx-llvm-backend/` | Compiler implementation |
| Emulator | `linx-skills/linx-isa-emulator/` | QEMU development |
| Manual | `linx-skills/linx-isa-manual/` | Documentation |
| RTL | `linx-skills/linx-rtl-development/` | Hardware development |

---

## Appendix C: Document References

| Document | Location |
|----------|----------|
| ISA Manual | `docs/architecture/isa-manual/` |
| JSON Spec | `isa/spec/current/linxisa-v0.2.json` |
| Golden Sources | `isa/golden/v0.2/` |
| Compiler Plan | `compiler/COMPILER_PLAN.md` |
| Bring-up Progress | `docs/bringup/PROGRESS.md` |
| Regression | `tools/regression/run.sh` |

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-11  
**Next Review:** 2026-02-18
