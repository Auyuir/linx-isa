#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


BENCH_DIR = Path(__file__).resolve().parent
WORKLOADS_DIR = BENCH_DIR.parent
REPO_ROOT = WORKLOADS_DIR.parent

LIBC_DIR = REPO_ROOT / "toolchain" / "libc"
LIBC_INCLUDE = LIBC_DIR / "include"
LIBC_SRC = LIBC_DIR / "src"


_RE_OBJDUMP_INSN = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2})*)\s+(.*)$"
)


def _run(cmd: list[str], *, cwd: Path | None = None, verbose: bool = False, **kwargs) -> subprocess.CompletedProcess[bytes]:
    if verbose:
        print("+", " ".join(cmd), file=sys.stderr)
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False, **kwargs)


def _check_exe(p: Path, what: str) -> None:
    if not p.exists():
        raise SystemExit(f"error: {what} not found: {p}")
    if not os.access(p, os.X_OK):
        raise SystemExit(f"error: {what} not executable: {p}")


def _default_clang() -> Path | None:
    env = os.environ.get("CLANG")
    if env:
        return Path(os.path.expanduser(env))
    cand = Path.home() / "llvm-project" / "build-linxisa-clang" / "bin" / "clang"
    return cand if cand.exists() else None


def _default_lld(clang: Path | None) -> Path | None:
    env = os.environ.get("LLD")
    if env:
        return Path(os.path.expanduser(env))
    if clang:
        cand = clang.parent / "ld.lld"
        if cand.exists():
            return cand
    return None


def _default_llvm_tool(clang: Path, tool: str) -> Path | None:
    cand = clang.parent / tool
    return cand if cand.exists() else None


def _default_qemu() -> Path | None:
    env = os.environ.get("QEMU")
    if env:
        return Path(os.path.expanduser(env))
    cand = Path.home() / "qemu" / "build" / "qemu-system-linx64"
    cand_tci = Path.home() / "qemu" / "build-tci" / "qemu-system-linx64"

    # Prefer the full build when present: some TCI builds are configured without
    # plugin support, which breaks `--dynamic-hist`.
    if cand.exists():
        return cand
    if cand_tci.exists():
        return cand_tci
    return None


@dataclass(frozen=True)
class BenchResult:
    name: str
    elf: Path
    bin_path: Path
    objdump_path: Path
    qemu_stdout_path: Path
    qemu_stderr_path: Path
    qemu_dyn_hist_path: Path | None
    exit_code: int
    dyn_insn_count: int | None
    dyn_hist_total: int | None
    dyn_mnemonic_hist: dict[str, int] | None
    static_insn_count: int
    static_len_hist: dict[int, int]
    static_mnemonic_hist: dict[str, int]
    static_type_hist: dict[str, int]
    dyn_type_hist: dict[str, int] | None


def _parse_objdump(objdump_text: str) -> tuple[int, dict[int, int], dict[str, int]]:
    static_count = 0
    len_hist: dict[int, int] = defaultdict(int)
    mnem_hist: Counter[str] = Counter()

    for line in objdump_text.splitlines():
        m = _RE_OBJDUMP_INSN.match(line)
        if not m:
            continue
        bytes_text = m.group(2)
        insn_text = m.group(3).strip()

        byte_tokens = bytes_text.split()
        if not byte_tokens:
            continue
        enc_bits = len(byte_tokens) * 8

        # llvm-objdump uses tabs between mnemonic/operands for Linx; split on whitespace.
        parts = insn_text.split()
        if not parts:
            continue
        mnemonic = parts[0]

        static_count += 1
        len_hist[enc_bits] += 1
        mnem_hist[mnemonic] += 1

    return static_count, dict(sorted(len_hist.items())), dict(mnem_hist)


def _parse_linx_insn_count(stdout: bytes, stderr: bytes) -> int | None:
    text = (stderr or b"") + b"\n" + (stdout or b"")
    m = None
    for mm in re.finditer(rb"LINX_INSN_COUNT=(\d+)", text):
        m = mm
    if not m:
        return None
    return int(m.group(1), 10)

def _load_dyn_hist(path: Path) -> tuple[int | None, dict[str, int] | None]:
    """
    Load the dynamic histogram produced by `tools/qemu_plugins/linx_insn_hist.c`.
    Returns (total_insns, mnemonic->count) or (None, None) on failure.
    """
    if not path.exists():
        return None, None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        total = data.get("total_insns", None)
        all_map = data.get("all", None)
        if not isinstance(total, int) or not isinstance(all_map, dict):
            return None, None
        out: dict[str, int] = {}
        for k, v in all_map.items():
            if isinstance(k, str) and isinstance(v, int):
                out[k] = v
        return total, out
    except Exception:
        return None, None


def _classify_mnemonic(mnemonic: str) -> str:
    m = mnemonic.strip().lower()

    if m.startswith("c."):
        m = m[2:]
    if m.startswith("hl."):
        m = m[3:]

    if m.startswith(("v", "vec", "simd")):
        return "vector"

    if m.startswith(("f",)):
        return "floating-point"

    if (
        "bstart" in m
        or m.startswith(("br", "j", "call", "ret", "fret", "fentry", "setret"))
        or "branch" in m
    ):
        return "control-flow"

    if m.startswith(("ld", "st", "lw", "sw", "lb", "sb", "lh", "sh", "lwu", "sdi", "ldi")):
        return "memory"

    if m.startswith(("and", "or", "xor", "not", "sll", "srl", "sra", "rol", "ror")):
        return "bitwise-shift"

    if m.startswith(("setc", "cmp")):
        return "compare-condition"

    if m.startswith(("add", "sub", "mul", "div", "rem", "mov", "neg", "sext")):
        return "integer-alu"

    if m.startswith(("csr", "sys", "ecall", "ebreak", "fence", "mret", "sret", "wfi")):
        return "system"

    return "other"


def _build_type_hist(mnemonic_hist: dict[str, int]) -> dict[str, int]:
    out: Counter[str] = Counter()
    for mnemonic, count in mnemonic_hist.items():
        out[_classify_mnemonic(mnemonic)] += count
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _require_output_contains(
    *,
    name: str,
    haystack: str,
    needle: str,
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    if needle in haystack:
        return
    raise SystemExit(
        f"error: benchmark failed validation: {name}\n"
        f"  expected output to contain: {needle!r}\n"
        f"  stdout: {stdout_path}\n"
        f"  stderr: {stderr_path}\n"
    )


def _require_output_not_contains(
    *,
    name: str,
    haystack: str,
    needle: str,
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    if needle not in haystack:
        return
    raise SystemExit(
        f"error: benchmark failed validation: {name}\n"
        f"  unexpected output contained: {needle!r}\n"
        f"  stdout: {stdout_path}\n"
        f"  stderr: {stderr_path}\n"
    )


def _validate_benchmark_output(
    *,
    name: str,
    stdout_bytes: bytes,
    stderr_bytes: bytes,
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    text = (stdout_bytes or b"").decode("utf-8", errors="replace")
    text += "\n"
    text += (stderr_bytes or b"").decode("utf-8", errors="replace")

    if name == "coremark":
        _require_output_contains(
            name=name,
            haystack=text,
            needle="Correct operation validated.",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        _require_output_not_contains(
            name=name,
            haystack=text,
            needle="Errors detected",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        _require_output_not_contains(
            name=name,
            haystack=text,
            needle="ERROR!",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        return

    if name == "dhrystone":
        _require_output_contains(
            name=name,
            haystack=text,
            needle="Correct operation validated.",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        return

    # Unknown benchmark: no validation.


def _build_runtime_objects(
    clang: Path,
    target: str,
    out_dir: Path,
    *,
    verbose: bool,
) -> list[Path]:
    rt_dir = out_dir / "_runtime"
    rt_dir.mkdir(parents=True, exist_ok=True)

    cflags_base = [
        "-target",
        target,
        "-O2",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-stack-protector",
        "-fno-asynchronous-unwind-tables",
        "-fno-unwind-tables",
        "-fno-exceptions",
        "-fno-jump-tables",
        "-nostdlib",
        f"-I{LIBC_INCLUDE}",
        f"-I{BENCH_DIR}",
    ]

    def cc(src: Path, obj_name: str, extra: list[str] | None = None) -> Path:
        obj = rt_dir / obj_name
        cflags = list(cflags_base)
        if extra:
            cflags += extra
        cmd = [str(clang), *cflags, "-c", str(src), "-o", str(obj)]
        p = _run(cmd, verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            sys.stderr.buffer.write(p.stderr)
            raise SystemExit(f"error: runtime compile failed: {src}")
        return obj

    objs: list[Path] = []
    objs.append(cc(BENCH_DIR / "common" / "startup.c", "startup.o"))

    objs.append(cc(LIBC_SRC / "syscall.c", "syscall.o"))
    objs.append(cc(LIBC_SRC / "stdio" / "stdio.c", "stdio.o"))
    objs.append(cc(LIBC_SRC / "stdlib" / "stdlib.c", "stdlib.o"))
    objs.append(cc(LIBC_SRC / "string" / "mem.c", "mem.o"))
    objs.append(cc(LIBC_SRC / "string" / "str.c", "str.o"))
    # math is small; keep it for any incidental uses.
    objs.append(cc(LIBC_SRC / "math" / "math.c", "math.o"))

    return objs


def _build_benchmark_elf(
    *,
    name: str,
    clang: Path,
    lld: Path,
    llvm_objdump: Path,
    llvm_objcopy: Path,
    qemu: Path,
    target: str,
    runtime_objs: list[Path],
    sources: list[Path],
    include_dirs: list[Path],
    cflags_extra: list[str],
    out_dir: Path,
    artifacts_dir: Path,
    verbose: bool,
    qemu_timeout_s: float,
    qemu_args_extra: list[str],
) -> BenchResult:
    obj_dir = out_dir / name / "obj"
    obj_dir.mkdir(parents=True, exist_ok=True)

    common_cflags = [
        "-target",
        target,
        "-O2",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-stack-protector",
        "-fno-asynchronous-unwind-tables",
        "-fno-unwind-tables",
        "-fno-exceptions",
        "-fno-jump-tables",
        "-nostdlib",
        f"-I{LIBC_INCLUDE}",
        f"-I{BENCH_DIR}",
        *[f"-I{p}" for p in include_dirs],
        *cflags_extra,
    ]

    objects: list[Path] = []
    for src in sources:
        obj = obj_dir / (src.stem + ".o")
        per_src_flags: list[str] = []
        if name == "coremark" and src.name == "core_list_join.c":
            # Work around a Linx LLVM backend miscompile of the list-reversal
            # path at -O2 (breaks CoreMark CRC validation).
            per_src_flags.append("-O0")

        cmd = [str(clang), *common_cflags, *per_src_flags, "-c", str(src), "-o", str(obj)]
        p = _run(cmd, verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            sys.stderr.buffer.write(p.stderr)
            raise SystemExit(f"error: compile failed: {src}")
        objects.append(obj)

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    elf_dir = artifacts_dir / "elf"
    bin_dir = artifacts_dir / "bin"
    objdump_dir = artifacts_dir / "objdump"
    qemu_dir = artifacts_dir / "qemu"
    elf_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    objdump_dir.mkdir(parents=True, exist_ok=True)
    qemu_dir.mkdir(parents=True, exist_ok=True)

    elf = elf_dir / f"{name}.elf"
    link_cmd = [
        str(lld),
        "--entry=_start",
        "-o",
        str(elf),
        *[str(o) for o in runtime_objs],
        *[str(o) for o in objects],
    ]
    p = _run(link_cmd, verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"error: link failed: {name}")

    objdump_path = objdump_dir / f"{name}.objdump.txt"
    p = _run(
        [str(llvm_objdump), "-d", f"--triple={target}", str(elf)],
        verbose=verbose,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"error: llvm-objdump failed: {name}")
    objdump_path.write_bytes(p.stdout)

    bin_path = bin_dir / f"{name}.bin"
    p = _run(
        [str(llvm_objcopy), "--only-section=.text", "-O", "binary", str(elf), str(bin_path)],
        verbose=verbose,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"error: llvm-objcopy failed: {name}")

    static_insn_count, static_len_hist, static_mnemonic_hist = _parse_objdump(
        objdump_path.read_text(encoding="utf-8", errors="replace")
    )

    qemu_stdout_path = qemu_dir / f"{name}.stdout.txt"
    qemu_stderr_path = qemu_dir / f"{name}.stderr.txt"
    qemu_dyn_hist_path: Path | None = None

    qemu_cmd = [
        str(qemu),
        "-machine",
        "virt",
        "-kernel",
        str(elf),
        "-nographic",
        "-monitor",
        "none",
        *qemu_args_extra,
    ]

    dyn_hist_total: int | None = None
    dyn_hist_map: dict[str, int] | None = None
    plugin_path = os.environ.get("LINX_INSN_HIST_PLUGIN", "")
    if plugin_path:
        qemu_dyn_hist_path = qemu_dir / f"{name}.dyn_insn_hist.json"
        qemu_cmd += ["-plugin", f"{plugin_path},out={qemu_dyn_hist_path},top=200"]
    try:
        p = _run(
            qemu_cmd,
            verbose=verbose,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=qemu_timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or b""
        stderr = e.stderr or b""
        qemu_stdout_path.write_bytes(stdout)
        qemu_stderr_path.write_bytes(stderr)
        raise SystemExit(f"error: QEMU timeout after {qemu_timeout_s:.1f}s: {name}")

    qemu_stdout_path.write_bytes(p.stdout or b"")
    qemu_stderr_path.write_bytes(p.stderr or b"")

    dyn_insn = _parse_linx_insn_count(p.stdout or b"", p.stderr or b"")
    if qemu_dyn_hist_path:
        dyn_hist_total, dyn_hist_map = _load_dyn_hist(qemu_dyn_hist_path)

    if p.returncode != 0:
        raise SystemExit(
            f"error: benchmark failed: {name} (qemu exit={p.returncode})\n"
            f"  stdout: {qemu_stdout_path}\n"
            f"  stderr: {qemu_stderr_path}\n"
        )

    _validate_benchmark_output(
        name=name,
        stdout_bytes=p.stdout or b"",
        stderr_bytes=p.stderr or b"",
        stdout_path=qemu_stdout_path,
        stderr_path=qemu_stderr_path,
    )

    return BenchResult(
        name=name,
        elf=elf,
        bin_path=bin_path,
        objdump_path=objdump_path,
        qemu_stdout_path=qemu_stdout_path,
        qemu_stderr_path=qemu_stderr_path,
        qemu_dyn_hist_path=qemu_dyn_hist_path,
        exit_code=p.returncode,
        dyn_insn_count=dyn_insn,
        dyn_hist_total=dyn_hist_total,
        dyn_mnemonic_hist=dyn_hist_map,
        static_insn_count=static_insn_count,
        static_len_hist=static_len_hist,
        static_mnemonic_hist=static_mnemonic_hist,
        static_type_hist=_build_type_hist(static_mnemonic_hist),
        dyn_type_hist=_build_type_hist(dyn_hist_map) if dyn_hist_map else None,
    )


def _format_hist_top(m: dict[str, int], *, total: int, top_n: int = 16) -> str:
    items = sorted(m.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    lines = ["| Mnemonic | Count | % |", "|---|---:|---:|"]
    for k, v in items:
        pct = (100.0 * v / total) if total else 0.0
        lines.append(f"| `{k}` | {v} | {pct:5.2f} |")
    return "\n".join(lines)


def _format_len_hist(h: dict[int, int], *, total: int) -> str:
    lines = ["| Encoding | Count | % |", "|---|---:|---:|"]
    for bits, count in sorted(h.items()):
        pct = (100.0 * count / total) if total else 0.0
        lines.append(f"| {bits:>2}b | {count} | {pct:5.2f} |")
    return "\n".join(lines)


def _format_type_hist(h: dict[str, int], *, total: int) -> str:
    lines = ["| Type | Count | % |", "|---|---:|---:|"]
    for k, v in sorted(h.items(), key=lambda kv: (-kv[1], kv[0])):
        pct = (100.0 * v / total) if total else 0.0
        lines.append(f"| `{k}` | {v} | {pct:5.2f} |")
    return "\n".join(lines)


def write_report(results: list[BenchResult], report_path: Path) -> None:
    lines: list[str] = []
    lines.append("# LinxISA Benchmarks Report\n")
    lines.append(f"Generated by `workloads/benchmarks/run_benchmarks.py`.\n")

    lines.append("## Summary\n")
    lines.append("| Benchmark | Static insts | Dynamic insts (QEMU) | Artifacts |")
    lines.append("|---|---:|---:|---|")
    for r in results:
        dyn = str(r.dyn_insn_count) if r.dyn_insn_count is not None else "N/A"
        artifacts = f"`{r.elf}` / `{r.bin_path}` / `{r.objdump_path}`"
        lines.append(f"| `{r.name}` | {r.static_insn_count} | {dyn} | {artifacts} |")
    lines.append("")

    for r in results:
        lines.append(f"## {r.name}\n")
        dyn = str(r.dyn_insn_count) if r.dyn_insn_count is not None else "N/A"
        lines.append(f"- Static instruction count: `{r.static_insn_count}`")
        lines.append(f"- Dynamic instruction count (QEMU): `{dyn}`")
        if r.dyn_hist_total is not None:
            lines.append(f"- Dynamic histogram total (plugin): `{r.dyn_hist_total}`")
        if r.qemu_dyn_hist_path:
            lines.append(f"- Dynamic histogram: `{r.qemu_dyn_hist_path}`")
        lines.append(f"- QEMU logs: `{r.qemu_stdout_path}` / `{r.qemu_stderr_path}`\n")

        lines.append("### Static instruction-length histogram\n")
        lines.append(_format_len_hist(r.static_len_hist, total=r.static_insn_count))
        lines.append("")

        lines.append("### Static opcode histogram (top)\n")
        lines.append(_format_hist_top(r.static_mnemonic_hist, total=r.static_insn_count, top_n=20))
        lines.append("")
        lines.append("### Instruction type histogram\n")
        lines.append(_format_type_hist(r.static_type_hist, total=r.static_insn_count))
        lines.append("")

        dyn_total_for_pct = r.dyn_hist_total if r.dyn_hist_total is not None else r.dyn_insn_count
        if r.dyn_mnemonic_hist and dyn_total_for_pct:
            lines.append("### Dynamic opcode histogram (top)\n")
            lines.append(_format_hist_top(r.dyn_mnemonic_hist, total=dyn_total_for_pct, top_n=20))
            lines.append("")
            if r.dyn_type_hist:
                lines.append("### Dynamic instruction type histogram\n")
                lines.append(_format_type_hist(r.dyn_type_hist, total=dyn_total_for_pct))
                lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build + run CoreMark and Dhrystone on LinxISA QEMU.")
    ap.add_argument("--clang", default=None, help="Path to clang (env: CLANG)")
    ap.add_argument("--lld", default=None, help="Path to ld.lld (env: LLD)")
    ap.add_argument("--qemu", default=None, help="Path to qemu-system-linx64 (env: QEMU)")
    ap.add_argument("--target", default="linx64-linx-none-elf", help="Target triple")
    ap.add_argument("--timeout", type=float, default=30.0, help="QEMU timeout (seconds)")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose build/run commands")
    ap.add_argument(
        "--dynamic-hist",
        action="store_true",
        help="Enable dynamic per-mnemonic histogram via QEMU plugin (requires LINX_INSN_HIST_PLUGIN).",
    )
    args = ap.parse_args(argv)

    clang = Path(os.path.expanduser(args.clang)) if args.clang else (_default_clang() or None)
    if not clang:
        raise SystemExit("error: clang not found; set --clang or CLANG")
    lld = Path(os.path.expanduser(args.lld)) if args.lld else (_default_lld(clang) or None)
    if not lld:
        raise SystemExit("error: ld.lld not found; set --lld or LLD")
    qemu = Path(os.path.expanduser(args.qemu)) if args.qemu else (_default_qemu() or None)
    if not qemu:
        raise SystemExit("error: qemu-system-linx64 not found; set --qemu or QEMU")

    llvm_objdump = _default_llvm_tool(clang, "llvm-objdump")
    llvm_objcopy = _default_llvm_tool(clang, "llvm-objcopy")
    if not llvm_objdump or not llvm_objcopy:
        raise SystemExit("error: llvm-objdump/llvm-objcopy not found next to clang")

    _check_exe(clang, "clang")
    _check_exe(lld, "ld.lld")
    _check_exe(qemu, "qemu-system-linx64")
    _check_exe(llvm_objdump, "llvm-objdump")
    _check_exe(llvm_objcopy, "llvm-objcopy")

    generated_dir = WORKLOADS_DIR / "generated"
    out_dir = generated_dir / "build"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.dynamic_hist and not os.environ.get("LINX_INSN_HIST_PLUGIN"):
        raise SystemExit(
            "error: --dynamic-hist requires LINX_INSN_HIST_PLUGIN=/path/to/liblinx_insn_hist.so\n"
            "hint: build it with: bash tools/qemu_plugins/build_linx_insn_hist.sh"
        )

    runtime_objs = _build_runtime_objects(clang, args.target, out_dir, verbose=args.verbose)

    results: list[BenchResult] = []

    # CoreMark
    coremark_up = BENCH_DIR / "coremark" / "upstream"
    coremark_port = BENCH_DIR / "coremark" / "linx"
    coremark_sources = [
        coremark_up / "core_list_join.c",
        coremark_up / "core_main.c",
        coremark_up / "core_matrix.c",
        coremark_up / "core_state.c",
        coremark_up / "core_util.c",
        coremark_port / "core_portme.c",
    ]
    coremark_cflags = [
        # CoreMark expects these from the build system.
        '-DFLAGS_STR="-O2 (core_list_join:-O0) -ffreestanding -nostdlib"',
        "-O2",
        "-DITERATIONS=1",
    ]
    results.append(
        _build_benchmark_elf(
            name="coremark",
            clang=clang,
            lld=lld,
            llvm_objdump=llvm_objdump,
            llvm_objcopy=llvm_objcopy,
            qemu=qemu,
            target=args.target,
            runtime_objs=runtime_objs,
            sources=coremark_sources,
            include_dirs=[coremark_up, coremark_port],
            cflags_extra=coremark_cflags,
            out_dir=out_dir,
            artifacts_dir=generated_dir,
            verbose=args.verbose,
            qemu_timeout_s=args.timeout,
            qemu_args_extra=[],
        )
    )

    # Dhrystone
    dhry_src = BENCH_DIR / "dhrystone" / "linx"
    dhry_sources = [
        dhry_src / "dhry_1.c",
        dhry_src / "dhry_2.c",
    ]
    dhry_cflags = [
        "-std=gnu89",
        "-Wno-implicit-int",
        "-Wno-return-type",
        "-Wno-implicit-function-declaration",
        "-DDHRY_RUNS=1000",
    ]
    results.append(
        _build_benchmark_elf(
            name="dhrystone",
            clang=clang,
            lld=lld,
            llvm_objdump=llvm_objdump,
            llvm_objcopy=llvm_objcopy,
            qemu=qemu,
            target=args.target,
            runtime_objs=runtime_objs,
            sources=dhry_sources,
            include_dirs=[dhry_src],
            cflags_extra=dhry_cflags,
            out_dir=out_dir,
            artifacts_dir=generated_dir,
            verbose=args.verbose,
            qemu_timeout_s=args.timeout,
            qemu_args_extra=[],
        )
    )

    report_path = generated_dir / "report.md"
    write_report(results, report_path)
    print(f"ok: wrote {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
