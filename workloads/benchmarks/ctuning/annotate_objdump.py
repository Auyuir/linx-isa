#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_RE_RELOC = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+R_LINX_[A-Z0-9_]+\s+([^\s]+)\s*$"
)
_RE_INSN = re.compile(r"^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2})*)\s+(.*)$")


def _format_insn(addr_hex: str, bytes_text: str, insn_text: str) -> str:
    # Fixed-width columns:
    #   PC | BYTES (up to 64-bit) | ENC | OPCODE | OPERANDS | DEST
    #
    # BYTES column is sized for 8 bytes: "xx xx xx xx xx xx xx xx" (23 chars).
    pc = addr_hex.lower()
    try:
        pc = f"{int(pc, 16):016x}"
    except ValueError:
        pc = pc.rjust(16, "0")

    byte_list = bytes_text.split()
    enc_bits = len(byte_list) * 8
    enc = f"{enc_bits}bit"

    # Prefer tab-separated mnemonic/operands if present (llvm-objdump style).
    parts = insn_text.split("\t")
    if parts:
        opcode = parts[0].strip()
        operands = "\t".join(parts[1:]).strip() if len(parts) > 1 else ""
    else:
        opcode, _, operands = insn_text.strip().partition(" ")

    # Split operands at the last destination marker to keep `->...` aligned.
    dest = ""
    ops = operands
    idx = ops.rfind("->")
    if idx != -1:
        dest = ops[idx:].strip()
        ops = ops[:idx].rstrip().rstrip(",").rstrip()

    bytes_col = bytes_text.ljust(23)
    opcode_col = opcode.ljust(16)[:16]
    ops_col = ops.ljust(40)

    if dest:
        return f"{pc}: {bytes_col} {enc:<5} {opcode_col} {ops_col} {dest}\n"
    if ops:
        return f"{pc}: {bytes_col} {enc:<5} {opcode_col} {ops}\n"
    return f"{pc}: {bytes_col} {enc:<5} {opcode_col}\n"


def _rewrite_insn(insn_text: str, sym: str) -> str:
    # Try to replace a trailing immediate/address operand with the relocation symbol.
    # This targets the patterns produced by the Linx bring-up backend:
    #   lw.pcr 0x0, ->a2
    #   sw.pcr a2, 0x0
    #   C.BSTART COND, 0x168a
    #   BSTART CALL, 0x38
    #
    # We keep formatting stable and only replace the final hex token when present.
    parts = insn_text.split("\t")
    if not parts:
        return insn_text

    # If the instruction already prints a bracketed symbol operand (e.g.
    # `lw.pcr [sym+0x10], ->rd`), don't attempt to re-annotate the trailing
    # hex addend; otherwise we'd turn `[sym+0x10]` into `[sym+sym+0x10]`.
    if ".pcr" in insn_text and "[" in insn_text and "]" in insn_text:
        m = re.search(r"\[([^\]]+)\]", insn_text)
        if m and re.search(r"[A-Za-z_.]", m.group(1)):
            return insn_text

    # Special-case Linx formatted PCR loads:
    #   lw.pcr <addr>, ->rd
    # which prints as: ["lw.pcr", "<addr>,", "->rd"]
    if len(parts) >= 3 and parts[0].endswith(".pcr") and parts[2].lstrip().startswith("->"):
        op0 = parts[1]
        # Replace the last hex/0 token in the first operand field.
        op0, n = re.subn(r"\b0x[0-9a-fA-F]+\b(?!.*\b0x[0-9a-fA-F]+\b)", sym, op0)
        if not n:
            op0, n = re.subn(r"\b0\b(?!.*\b0\b)", sym, op0)
        if n:
            parts[1] = op0
            return "\t".join(parts)

    tail = parts[-1]

    # Replace the last "0x..." in the last tab-field.
    def repl(m: re.Match[str]) -> str:
        return sym

    new_tail, n = re.subn(r"\b0x[0-9a-fA-F]+\b(?!.*\b0x[0-9a-fA-F]+\b)", repl, tail)
    if n:
        parts[-1] = new_tail
        return "\t".join(parts)

    # Fallback: replace a trailing "0" immediate (common for PCR placeholders).
    new_tail, n = re.subn(r"\b0\b(?!.*\b0\b)", repl, tail)
    if n:
        parts[-1] = new_tail
        return "\t".join(parts)

    return insn_text


def annotate(lines: list[str]) -> list[str]:
    # Map relocation address -> symbol string.
    relocs: dict[int, str] = {}
    out = list(lines)

    # First pass: collect relocations.
    for line in lines:
        m = _RE_RELOC.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        sym = m.group(2)
        relocs[addr] = sym

    # Second pass: rewrite instruction lines.
    for idx, line in enumerate(lines):
        m = _RE_INSN.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        sym = relocs.get(addr)
        insn_text = m.group(3)
        if sym:
            insn_text = _rewrite_insn(insn_text, sym)
        out[idx] = _format_insn(m.group(1), m.group(2), insn_text)

    # Drop relocation records after folding their symbols into the instruction
    # operands. This keeps the annotated objdump compact while preserving the
    # information inline on the instruction itself.
    return [line for line in out if not _RE_RELOC.match(line)]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Annotate llvm-objdump output with relocation symbols.")
    ap.add_argument("input", type=Path, help="Input objdump text file.")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output annotated objdump text file.")
    args = ap.parse_args(argv)

    text = args.input.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    annotated = annotate(text)
    args.output.write_text("".join(annotated), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
