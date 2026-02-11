#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PTO_RUNNER = REPO_ROOT / "tools" / "pto" / "run_v03_pto_to_linx.sh"
PTO_OUT_DIR = REPO_ROOT / "tools" / "pto" / "out"

GENERATED_ROOT = REPO_ROOT / "workloads" / "generated"
OBJ_ROOT = GENERATED_ROOT / "elf" / "pto_ai"
OBJDUMP_ROOT = GENERATED_ROOT / "objdump" / "pto_ai"
REPORT_PATH = GENERATED_ROOT / "pto_ai_report.md"

KERNELS = {
    "tload_store": {
        "src": REPO_ROOT / "tools" / "pto" / "examples" / "pto_tload_store.cpp",
        "asm": PTO_OUT_DIR / "pto_tload_store.s",
        "require_all_hands": False,
    },
    "mamulb": {
        "src": REPO_ROOT / "tools" / "pto" / "examples" / "pto_mamulb.cpp",
        "asm": PTO_OUT_DIR / "pto_mamulb.s",
        "require_all_hands": False,
    },
    "tmatmul_acc": {
        "src": REPO_ROOT / "tools" / "pto" / "examples" / "pto_tmatmul_acc.cpp",
        "asm": PTO_OUT_DIR / "pto_tmatmul_acc.s",
        "require_all_hands": False,
    },
    "gemm_auto": {
        "src": REPO_ROOT / "tools" / "pto" / "examples" / "pto_gemm_auto.cpp",
        "asm": PTO_OUT_DIR / "pto_gemm_auto.s",
        "require_all_hands": True,
    },
    "flash_attention_auto": {
        "src": REPO_ROOT / "tools" / "pto" / "examples" / "pto_flash_attention_auto.cpp",
        "asm": PTO_OUT_DIR / "pto_flash_attention_auto.s",
        "require_all_hands": True,
    },
}

FORBIDDEN_RE = re.compile(r"((^|[^A-Za-z0-9_])L\.|set_flag|wait_flag|TSync|B\.SET|B\.WAIT)", re.IGNORECASE)
TILE_NUM_RE = re.compile(r"\btile([0-9]+)\b")
TILE_HAND_RE = re.compile(r"\b([tumn])#?([0-7])\b", re.IGNORECASE)
OBJDUMP_RE = re.compile(r"^\s*[0-9a-fA-F]+:\s+(?:[0-9a-fA-F]{2}\s+)+(.+)$")
TMA_HEADER_RE = re.compile(r"\bBSTART\.(?:TMA|PAR)\b.*\bT(?:LOAD|STORE)\b")


@dataclass(frozen=True)
class KernelResult:
    name: str
    obj: Path
    objdump: Path
    asm: Path
    static_insn_count: int
    tile_groups: tuple[bool, bool, bool, bool]
    require_all_hands: bool


def run(cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None, verbose: bool = False) -> subprocess.CompletedProcess[bytes]:
    if verbose:
        print("+", " ".join(cmd), file=sys.stderr)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def check_exe(path: Path, what: str) -> None:
    if not path.exists():
        raise SystemExit(f"error: {what} not found: {path}")
    if not os.access(path, os.X_OK):
        raise SystemExit(f"error: {what} is not executable: {path}")


def default_clangxx() -> Path:
    env = os.environ.get("CLANGXX") or os.environ.get("CLANG")
    if env:
        return Path(os.path.expanduser(env))
    candidate = Path.home() / "llvm-project" / "build-linxisa-clang" / "bin" / "clang++"
    if candidate.exists():
        return candidate
    raise SystemExit("error: clang++ not found; set CLANGXX or CLANG")


def default_clang(clangxx: Path) -> Path:
    env = os.environ.get("QEMU_CLANG") or os.environ.get("CLANG")
    if env:
        return Path(os.path.expanduser(env))
    sibling = clangxx.parent / "clang"
    if sibling.exists():
        return sibling
    return clangxx


def default_objdump(clangxx: Path) -> Path:
    env = os.environ.get("LLVM_OBJDUMP")
    if env:
        return Path(os.path.expanduser(env))
    sibling = clangxx.parent / "llvm-objdump"
    if sibling.exists():
        return sibling
    from shutil import which

    path = which("llvm-objdump")
    if path:
        return Path(path)
    raise SystemExit("error: llvm-objdump not found; set LLVM_OBJDUMP")


def parse_static_insn_count(objdump_text: str) -> int:
    count = 0
    for line in objdump_text.splitlines():
        if OBJDUMP_RE.match(line):
            count += 1
    return count


def parse_tile_groups(asm_text: str) -> tuple[bool, bool, bool, bool]:
    has_t = False
    has_u = False
    has_m = False
    has_n = False
    for match in TILE_NUM_RE.finditer(asm_text):
        tile = int(match.group(1), 10)
        if 0 <= tile <= 7:
            has_t = True
        elif 8 <= tile <= 15:
            has_u = True
        elif 16 <= tile <= 23:
            has_m = True
        elif 24 <= tile <= 31:
            has_n = True
    for match in TILE_HAND_RE.finditer(asm_text):
        hand = match.group(1).lower()
        if hand == "t":
            has_t = True
        elif hand == "u":
            has_u = True
        elif hand == "m":
            has_m = True
        elif hand == "n":
            has_n = True
    return has_t, has_u, has_m, has_n


def assert_no_forbidden_tokens(path: Path, text: str) -> None:
    match = FORBIDDEN_RE.search(text)
    if match:
        raise SystemExit(f"error: forbidden token '{match.group(0)}' in {path}")


def assert_tma_descriptor_headers(path: Path, asm_text: str) -> None:
    lines = asm_text.splitlines()
    block_start = 0
    while block_start < len(lines):
        line = lines[block_start]
        if not TMA_HEADER_RE.search(line):
            block_start += 1
            continue

        block_end = block_start + 1
        while block_end < len(lines) and "BSTART." not in lines[block_end]:
            block_end += 1
        block = "\n".join(lines[block_start:block_end])
        if "B.ARG" not in block:
            raise SystemExit(f"error: missing B.ARG in TMA block from {path}")
        if "B.IOR" not in block:
            raise SystemExit(f"error: missing B.IOR in TMA block from {path}")
        if "B.IOT" not in block:
            raise SystemExit(f"error: missing B.IOT/B.IOTI in TMA block from {path}")
        block_start = block_end


def run_v03_runner(clang: Path, clangxx: Path, *, skip_qemu: bool, verbose: bool) -> None:
    env = os.environ.copy()
    env["CLANG"] = str(clangxx)
    env["CLANGXX"] = str(clangxx)
    env["QEMU_CLANG"] = str(clang)
    env["RUN_QEMU_TILE"] = "0" if skip_qemu else "1"
    proc = run(["bash", str(PTO_RUNNER)], env=env, cwd=REPO_ROOT, verbose=verbose)
    if proc.returncode != 0:
        sys.stderr.buffer.write(proc.stdout)
        sys.stderr.buffer.write(proc.stderr)
        raise SystemExit("error: PTO v0.3 runner failed")


def compile_and_objdump_kernels(clangxx: Path, llvm_objdump: Path, *, verbose: bool) -> list[KernelResult]:
    OBJ_ROOT.mkdir(parents=True, exist_ok=True)
    OBJDUMP_ROOT.mkdir(parents=True, exist_ok=True)

    common_flags = [
        "-target",
        "linx64-linx-none-elf",
        "-O2",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-stack-protector",
        "-fno-exceptions",
        "-fno-rtti",
        "-nostdlib",
        f"-I{REPO_ROOT / 'toolchain' / 'pto' / 'include'}",
    ]

    results: list[KernelResult] = []
    for name, meta in KERNELS.items():
        src = meta["src"]
        asm = meta["asm"]
        obj = OBJ_ROOT / f"{name}.o"
        objdump = OBJDUMP_ROOT / f"{name}.objdump.txt"

        proc = run(
            [str(clangxx), *common_flags, "-c", str(src), "-o", str(obj)],
            cwd=REPO_ROOT,
            verbose=verbose,
        )
        if proc.returncode != 0:
            sys.stderr.buffer.write(proc.stdout)
            sys.stderr.buffer.write(proc.stderr)
            raise SystemExit(f"error: compile failed for {src}")

        proc = run([str(llvm_objdump), "-d", "-r", str(obj)], cwd=REPO_ROOT, verbose=verbose)
        if proc.returncode != 0:
            sys.stderr.buffer.write(proc.stdout)
            sys.stderr.buffer.write(proc.stderr)
            raise SystemExit(f"error: objdump failed for {obj}")
        objdump_text = proc.stdout.decode("utf-8", errors="replace")
        objdump.write_text(objdump_text, encoding="utf-8")

        if not asm.exists():
            raise SystemExit(f"error: expected asm output missing: {asm}")
        asm_text = asm.read_text(encoding="utf-8", errors="replace")
        assert_no_forbidden_tokens(asm, asm_text)
        assert_tma_descriptor_headers(asm, asm_text)
        tile_groups = parse_tile_groups(asm_text)
        require_all_hands = bool(meta.get("require_all_hands", False))
        if require_all_hands and not all(tile_groups):
            raise SystemExit(f"error: tile-group coverage incomplete in {asm}: {tile_groups}")

        results.append(
            KernelResult(
                name=name,
                obj=obj,
                objdump=objdump,
                asm=asm,
                static_insn_count=parse_static_insn_count(objdump_text),
                tile_groups=tile_groups,
                require_all_hands=require_all_hands,
            )
        )
    return results


def write_report(results: list[KernelResult], *, qemu_ran: bool, clangxx: Path, llvm_objdump: Path) -> None:
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# PTO AI kernels on LinxISA v0.3 (auto-mode only)")
    lines.append("")
    lines.append("## Validation Summary")
    lines.append(f"- PTO->Linx compile flow: `tools/pto/run_v03_pto_to_linx.sh`")
    lines.append(f"- QEMU tile execution: {'run (suite=tile, ids 0x000A0001..0x000A000A)' if qemu_ran else 'skipped'}")
    lines.append("- Auto-mode policy: no sync/set/wait flag tokens in canonical asm")
    lines.append("- Descriptor policy: each TMA block contains `B.ARG` + `B.IOR` + `B.IOT/B.IOTI`")
    lines.append("- Tile-group policy: `gemm_auto` and `flash_attention_auto` must use T/U/M/N hands")
    lines.append("")
    lines.append("## Toolchain")
    lines.append(f"- clang++: `{clangxx}`")
    lines.append(f"- llvm-objdump: `{llvm_objdump}`")
    lines.append("")
    lines.append("## Kernel Results")
    for result in results:
        t, u, m, n = result.tile_groups
        lines.append(f"### `{result.name}`")
        lines.append(f"- asm: `{result.asm}`")
        lines.append(f"- object: `{result.obj}`")
        lines.append(f"- objdump: `{result.objdump}`")
        lines.append(f"- static instruction count: {result.static_insn_count}")
        lines.append(f"- tile groups: T={t}, U={u}, M={m}, N={n}")
        lines.append(f"- full hand coverage required: {result.require_all_hands}")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Compile and validate PTO AI kernels on LinxISA v0.3.")
    parser.add_argument("--skip-qemu", action="store_true", help="Skip the tile QEMU run while still compiling kernels.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print commands as they run.")
    args = parser.parse_args(argv)

    clangxx = default_clangxx()
    clang = default_clang(clangxx)
    llvm_objdump = default_objdump(clangxx)
    check_exe(clangxx, "clang++")
    check_exe(clang, "clang")
    check_exe(llvm_objdump, "llvm-objdump")
    if not PTO_RUNNER.exists():
        raise SystemExit(f"error: missing PTO runner script: {PTO_RUNNER}")

    run_v03_runner(clang, clangxx, skip_qemu=args.skip_qemu, verbose=args.verbose)
    results = compile_and_objdump_kernels(clangxx, llvm_objdump, verbose=args.verbose)
    write_report(results, qemu_ran=not args.skip_qemu, clangxx=clangxx, llvm_objdump=llvm_objdump)

    print(f"ok: report written to {REPORT_PATH}")
    print(f"ok: objdump artifacts written under {OBJDUMP_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
