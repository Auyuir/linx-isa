# Code Density And Dynamic Instruction Reduction (Linux Kernel Driven)

This note turns the Linux-kernel static/dynamic instruction stats into a concrete optimization roadmap for LinxISA.

## Data Sources (Reproducible)

- Static (vmlinux objdump, block-aware patterns):
  - `workloads/generated/linux/build-linx-fixed/static_stats.md`
  - `workloads/generated/linux/build-linx-fixed/static_stats.json`
- Dynamic (QEMU boot sample, 30s histogram):
  - `workloads/generated/linux/build-linx-fixed/dynamic_stats.md`
  - `workloads/generated/qemu/linux/build-linx-fixed/boot_30s.dyn_insn_hist.json`

## Key Observations From The Current Kernel Snapshot

- Instruction length mix is already dominated by 16b/32b, so the biggest wins come from removing entire instructions (dynamic count), not only shrinking encodings.
- Linx block structure is visible in disassembly: `*.BSTART*` are frequent and block sizes are small (many 2-5 instruction blocks).
- Two-instruction blocks are common; the most frequent shapes include:
  - `C.BSTART ; c.setc.eq` (large) and `C.BSTART ; c.setc.ne`
  - `C.BSTART ; <small op>` (e.g. `c.movr`, `c.movi`, `sdi`, ...)
- Hot “extend/mask churn” shows up as:
  - explicit `sext.w` patterns (often materialized as `addw src, zero` then compressed to `c.sext.w`)
  - explicit `zext.w` patterns (often `andiw` or shift-pairs)
- PC-relative symbol access exists (`*.PCR`), but there are still many cases where codegen falls back to address-materialization sequences, reducing density.

## Block-Aware Pattern Counting (Tooling Contract)

Statistical pattern analysis must respect block boundaries:

- `BSTART` begins a block (e.g. `C.BSTART`, `HL.BSTART.STD`, `BSTART.*`).
- `BSTOP`/`BSTACK` (if present) terminate a block.
- N-gram patterns must not cross blocks.

Implementation: `tools/analysis/objdump_stats.py` resets its n-gram window at block boundaries and additionally reports:

- block length histogram
- top two-instruction block shapes

## 1) “BEQ/HL.BEQ” Fused Alias (No New CBR ISA Needed)

Constraint: Linx block encoding places the `BSTART(..., branch_offset)` before the `SETC.*` compare, so a classic compare+branch fused instruction (CBR) is awkward.

Instead, define fused *aliases* for the common two-instruction conditional blocks:

- `BEQ`  = `C.BSTART COND,<target>` + `C.SETC.EQ <lhs>,<rhs>`
- `BNE`  = `C.BSTART COND,<target>` + `C.SETC.NE <lhs>,<rhs>`
- `HL.BEQ`/`HL.BNE` similarly, when the target is out of compressed range (or to force a longer form).

Where this helps:

- It makes this very common shape explicit, enabling compiler and assembler to treat it as a single semantic unit.
- It enables targeted peepholes: only emit the fused alias when the block has exactly two instructions.

Required toolchain work:

- Assembler: accept `beq/bne` as pseudo that expands to `bstart.cond + setc.*` in the correct order.
- Disassembler: optionally re-sugar the two-instruction block back into `beq/bne` for readability.
- LLVM Blockify: when a block’s entire body is exactly `{BSTART.COND, SETC.EQ/NE}`, emit the fused alias in the MIR-level representation so later passes can reason about it.

## 2) Producer-Does-Extend Using `SrcRType` (`.sw` / `.uw`)

Goal: remove explicit `sext.w` / `zext.w` instructions by tagging consumers.

Mechanism already present in ISA encoding for many 32b/48b forms:

- `SrcRType` is a 2-bit field:
  - `0`: `.sw`  (sign-extend low 32 bits)
  - `1`: `.uw`  (zero-extend low 32 bits)
  - `2`: `.neg/.not` (existing use)
  - `3`: none

Encoding suggestions (concrete, non-conflicting):

1. Keep compressed `C.SETC.*` as-is (no `SrcRType` bits available).
2. Prefer **promotion** from `{c.sext.w + C.SETC.*}` (2x16b) to `{SETC.* with SrcRType}` (1x32b) when it deletes an instruction:
   - size stays ~constant, dynamic instruction count drops.
3. Expand the same policy to `CMP.*` when its `SrcRType` is available:
   - fold local `sext.w`/`zext.w` producers into `cmp.* <lhs>, <rhs.{sw|uw}>`
4. For additional ALU ops (future work), do not try to retrofit `.sw/.uw` into 16b compressed encodings; prefer:
   - a 32b “typed-srcR” variant in unused encoding space, or
   - an HL.* long form that carries `SrcRType` when 32b space is tight.

Compiler work required:

- Add a distinct MI-operand flag for `.sw` (in addition to `.uw`).
- Peepholes:
  - fold local `sext.w` producers feeding `SETC/CMP` into `SrcRType=.sw`
  - fold local `zext.w` producers feeding `SETC/CMP` into `SrcRType=.uw`
- Heuristic:
  - allow selecting 32b SETC/CMP with `SrcRType` when it replaces (removes) one or more instructions.

## 3) PC-Relative Codegen Must Prefer `*.PCR` (Load/Store Exactly PC-Relative)

Policy:

- Global/constpool loads/stores should prefer `LB/LH/LW/LD.PCR` and `SB/SH/SW/SD.PCR`.
- Out-of-range should be handled by relaxation to `HL.*.PCR` (not by falling back to general address materialization).

LLVM lowering strategy:

- Keep `GlobalAddress` lowering as PC-relative (page+low) only as an *internal* representation.
- In DAG-to-DAG isel, aggressively fold:
  - `addr = ADDI(ADDTPC(sym), sym) [+ const]`
  - `load/store [addr]`
  - into `*.PCR` forms.
- Make the folding robust to equivalent (but not pointer-identical) symbol nodes.

## 4) Use Existing Bit-Manip + CONCAT Aggressively

Already in ISA:

- `BXU` / `BXS`: bitfield extract unsigned/signed
- `BCNT`: popcount
- `CONCAT`: enables barrel-shift style patterns by concatenating `(srcL,srcR)` then shifting.

Required LLVM work:

- TableGen / DAG combines:
  - `sll; srl/sra` -> `BXU/BXS` (already present as a peephole in Blockify; ensure it triggers on more shapes)
  - `popcount` -> `BCNT`
  - `rotl/rotr` -> `CONCAT + shift` sequences (or a dedicated pattern if one exists)

## 5) Template Blocks: `MCOPY` / `MSET` (Library + Accelerator Path)

Already in ISA:

- `MCOPY` template block for `memcpy/memmove`
- `MSET` template block for `memset`

Roadmap:

1. libc implements hand-written entry points that map to these templates for common size/align ranges.
2. LLVM recognizes builtin patterns and selects templates (or calls libc stubs) depending on size thresholds.
3. Later: identify additional kernel hot regions and define more template blocks so the CPU can offload to ASIC components.

## Suggested Next Measurements

- Re-run kernel static+dynamic stats after each compiler change (same build dir, same QEMU window):
  - track `C.SETC.*`, `C.SEXT.W`, `ANDIW`, `HL.LUI`, `*.PCR` frequencies.
- Add dynamic “top PCs” to the QEMU plugin (PC->count) to localize hotspots to functions/symbols.
- Add a “two-instruction block candidate report” that specifically counts:
  - `C.BSTART ; c.setc.eq/ne` and branch-target reachability classes.

