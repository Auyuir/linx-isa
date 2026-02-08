#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKLOADS_DIR = REPO_ROOT / "workloads"
GENERATED_DIR = WORKLOADS_DIR / "generated"


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


def _default_qemu() -> Path | None:
    env = os.environ.get("QEMU")
    if env:
        return Path(os.path.expanduser(env))
    cand = Path.home() / "qemu" / "build" / "qemu-system-linx64"
    cand_tci = Path.home() / "qemu" / "build-tci" / "qemu-system-linx64"

    # Prefer the full build when present: some TCI builds are configured
    # without plugin support.
    if cand.exists():
        return cand
    return cand_tci if cand_tci.exists() else None


def _default_plugin() -> Path:
    return GENERATED_DIR / "plugins" / "liblinx_insn_hist.so"


def _build_plugin(*, verbose: bool) -> Path:
    plugin = _default_plugin()
    if plugin.exists():
        return plugin
    cmd = ["bash", str(REPO_ROOT / "tools" / "qemu_plugins" / "build_linx_insn_hist.sh")]
    p = _run(cmd, cwd=REPO_ROOT, verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit("error: failed to build QEMU insn-hist plugin")
    if not plugin.exists():
        raise SystemExit(f"error: plugin build succeeded but output missing: {plugin}")
    return plugin


def _load_hist(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    m = data.get("all", {})
    if not isinstance(m, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in m.items():
        if isinstance(k, str) and isinstance(v, int):
            out[k] = v
    return out


def _load_hist_total(path: Path) -> int | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        total = data.get("total_insns", None)
        return total if isinstance(total, int) else None
    except Exception:
        return None


_RE_LINX_INSN_COUNT = re.compile(r"LINX_INSN_COUNT=(\d+)")


def _load_qemu_insn_count(stderr_path: Path) -> int | None:
    if not stderr_path.exists():
        return None
    text = stderr_path.read_text(encoding="utf-8", errors="replace")
    m = None
    for mm in _RE_LINX_INSN_COUNT.finditer(text):
        m = mm
    if not m:
        return None
    return int(m.group(1), 10)


_RE_OBJDUMP_INSN = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2})*)\s+(.*)$"
)


def _parse_objdump(path: Path) -> tuple[int, dict[int, int], dict[str, int]]:
    static_count = 0
    len_hist: dict[int, int] = defaultdict(int)
    mnem_hist: Counter[str] = Counter()

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _RE_OBJDUMP_INSN.match(line)
        if not m:
            continue
        byte_tokens = m.group(2).split()
        if not byte_tokens:
            continue
        enc_bits = len(byte_tokens) * 8
        insn_text = m.group(3).strip()
        toks = insn_text.split()
        if not toks:
            continue
        mnemonic = toks[0]
        static_count += 1
        len_hist[enc_bits] += 1
        mnem_hist[mnemonic] += 1

    return static_count, dict(sorted(len_hist.items())), dict(mnem_hist)


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


def _type_hist(m: dict[str, int]) -> dict[str, int]:
    out: Counter[str] = Counter()
    for k, v in m.items():
        out[_classify_mnemonic(k)] += v
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _format_top(hist: dict[str, int], *, top: int = 20) -> str:
    c = Counter(hist)
    items = c.most_common(top)
    lines = ["| Mnemonic | Count |", "|---|---:|"]
    for m, v in items:
        lines.append(f"| `{m}` | {v} |")
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


@dataclass(frozen=True)
class PortfolioItem:
    name: str
    static_objdump: Path | None
    dyn_hist: Path | None
    qemu_stderr: Path | None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Run a LinxISA benchmark portfolio and collect instruction stats.")
    ap.add_argument("--target", default="linx64-linx-none-elf")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--ctuning-limit", type=int, default=5, help="How many Milepost codelets to run (0=skip).")
    ap.add_argument("--polybench", action="store_true", help="Run a small PolyBench/C subset (freestanding port).")
    ap.add_argument("--polybench-kernels", default="gemm,jacobi-2d", help="Comma-separated PolyBench kernels to run.")
    args = ap.parse_args(argv)

    clang = _default_clang()
    if not clang:
        raise SystemExit("error: clang not found; set CLANG or install to ~/llvm-project/build-linxisa-clang/bin/clang")
    lld = _default_lld(clang)
    if not lld:
        raise SystemExit("error: ld.lld not found next to clang; set LLD")
    qemu = _default_qemu()
    if not qemu:
        raise SystemExit("error: qemu-system-linx64 not found; set QEMU")

    _check_exe(clang, "clang")
    _check_exe(lld, "ld.lld")
    _check_exe(qemu, "qemu-system-linx64")

    plugin = _build_plugin(verbose=args.verbose)
    os.environ["LINX_INSN_HIST_PLUGIN"] = str(plugin)

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    items: list[PortfolioItem] = []

    # CoreMark + Dhrystone (writes workloads/generated/report.md and objdumps).
    p = _run(
        [
            sys.executable,
            str(REPO_ROOT / "workloads" / "benchmarks" / "run_benchmarks.py"),
            "--target",
            args.target,
            "--timeout",
            str(args.timeout),
            "--dynamic-hist",
        ],
        cwd=REPO_ROOT,
        verbose=args.verbose,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stdout)
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit("error: run_benchmarks.py failed")

    for name in ("coremark", "dhrystone"):
        items.append(
            PortfolioItem(
                name=name,
                static_objdump=GENERATED_DIR / "objdump" / f"{name}.objdump.txt",
                dyn_hist=GENERATED_DIR / "qemu" / f"{name}.dyn_insn_hist.json",
                qemu_stderr=GENERATED_DIR / "qemu" / f"{name}.stderr.txt",
            )
        )

    # PolyBench/C subset (optional; compute kernels).
    if args.polybench:
        p = _run(
            [
                sys.executable,
                str(REPO_ROOT / "workloads" / "benchmarks" / "run_polybench.py"),
                "--target",
                args.target,
                "--timeout",
                str(args.timeout),
                "--dynamic-hist",
                "--kernels",
                args.polybench_kernels,
            ],
            cwd=REPO_ROOT,
            verbose=args.verbose,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if p.returncode != 0:
            sys.stderr.buffer.write(p.stdout)
            sys.stderr.buffer.write(p.stderr)
            raise SystemExit("error: run_polybench.py failed")

        for k in [x.strip() for x in args.polybench_kernels.split(",") if x.strip()]:
            items.append(
                PortfolioItem(
                    name=f"polybench:{k}",
                    static_objdump=GENERATED_DIR / "objdump" / "polybench" / f"{k}.objdump.txt",
                    dyn_hist=GENERATED_DIR / "qemu" / f"polybench_{k}.dyn_insn_hist.json",
                    qemu_stderr=GENERATED_DIR / "qemu" / f"polybench_{k}.stderr.txt",
                )
            )

    # Milepost codelets (optional; provides extra "real C" workloads).
    if args.ctuning_limit and args.ctuning_limit > 0:
        objdump_dir = GENERATED_DIR / "objdump" / "ctuning"
        hist_dir = GENERATED_DIR / "qemu" / "ctuning"
        objdump_dir.mkdir(parents=True, exist_ok=True)
        hist_dir.mkdir(parents=True, exist_ok=True)

        out_dir = REPO_ROOT / "tools" / "ctuning" / "out"
        p = _run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "ctuning" / "run_milepost_codelets.py"),
                "--clang",
                str(clang),
                "--lld",
                str(lld),
                "--qemu",
                str(qemu),
                "--target",
                args.target,
                "--run",
                "--limit",
                str(args.ctuning_limit),
                "--timeout",
                str(min(args.timeout, 20.0)),
                "--objdump-dir",
                str(objdump_dir),
                "--insn-hist-plugin",
                str(plugin),
                "--insn-hist-out-dir",
                str(hist_dir),
            ],
            cwd=REPO_ROOT,
            verbose=args.verbose,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if p.returncode != 0:
            sys.stderr.buffer.write(p.stdout)
            sys.stderr.buffer.write(p.stderr)
            raise SystemExit("error: ctuning codelets failed")

        # Best-effort enumerate the produced hist files as portfolio items.
        for h in sorted(hist_dir.glob("*.dyn_insn_hist.json")):
            name = h.name.replace(".dyn_insn_hist.json", "")
            items.append(
                PortfolioItem(
                    name=f"ctuning:{name}",
                    static_objdump=objdump_dir / f"{name}.objdump.txt",
                    dyn_hist=h,
                    qemu_stderr=None,
                )
            )

    # Portfolio report.
    report = GENERATED_DIR / "portfolio_report.md"
    lines: list[str] = []
    lines.append("# LinxISA Portfolio Instruction Report\n")
    lines.append("Generated by `workloads/benchmarks/run_portfolio.py`.\n")
    lines.append("## Artifacts\n")
    lines.append(f"- Static objdumps: `{GENERATED_DIR / 'objdump'}`")
    lines.append(f"- Dynamic histograms: `{GENERATED_DIR / 'qemu'}`")
    lines.append(f"- Baseline report (CoreMark+Dhrystone): `{GENERATED_DIR / 'report.md'}`\n")

    lines.append("## Summary\n")
    lines.append("| Workload | Static insts | Dynamic insts (plugin) | Dynamic insts (QEMU) | Artifacts |")
    lines.append("|---|---:|---:|---:|---|")
    for it in items:
        static_count = "N/A"
        if it.static_objdump and it.static_objdump.exists():
            static_count = str(_parse_objdump(it.static_objdump)[0])
        dyn_total = "N/A"
        if it.dyn_hist and it.dyn_hist.exists():
            t = _load_hist_total(it.dyn_hist)
            dyn_total = str(t) if t is not None else "N/A"
        qemu_total = "N/A"
        if it.qemu_stderr and it.qemu_stderr.exists():
            t = _load_qemu_insn_count(it.qemu_stderr)
            qemu_total = str(t) if t is not None else "N/A"
        artifacts = []
        if it.static_objdump:
            artifacts.append(f"`{it.static_objdump}`")
        if it.dyn_hist:
            artifacts.append(f"`{it.dyn_hist}`")
        lines.append(f"| `{it.name}` | {static_count} | {dyn_total} | {qemu_total} | {' / '.join(artifacts)} |")
    lines.append("")

    for it in items:
        lines.append(f"## {it.name}\n")
        static_count = None
        static_len = None
        static_mnems = None
        if it.static_objdump and it.static_objdump.exists():
            static_count, static_len, static_mnems = _parse_objdump(it.static_objdump)
            lines.append(f"- Static objdump: `{it.static_objdump}`")
            lines.append(f"- Static instruction count: `{static_count}`\n")
            lines.append("### Static instruction-length histogram\n")
            lines.append(_format_len_hist(static_len, total=static_count))
            lines.append("")
            lines.append("### Static opcode histogram (top)\n")
            lines.append(_format_top(static_mnems, top=20))
            lines.append("")
            lines.append("### Static instruction type histogram\n")
            lines.append(_format_type_hist(_type_hist(static_mnems), total=static_count))
            lines.append("")
        if it.dyn_hist and it.dyn_hist.exists():
            dyn_total = _load_hist_total(it.dyn_hist)
            qemu_total = _load_qemu_insn_count(it.qemu_stderr) if it.qemu_stderr else None
            lines.append(f"- Dynamic histogram: `{it.dyn_hist}`")
            if dyn_total is not None:
                lines.append(f"- Dynamic instruction count (plugin): `{dyn_total}`")
            if qemu_total is not None:
                lines.append(f"- Dynamic instruction count (QEMU): `{qemu_total}`")
            lines.append("")

            hist = _load_hist(it.dyn_hist)
            lines.append("### Dynamic opcode histogram (top)\n")
            lines.append(_format_top(hist, top=20))
            lines.append("")
            if dyn_total is not None:
                lines.append("### Dynamic instruction type histogram\n")
                lines.append(_format_type_hist(_type_hist(hist), total=dyn_total))
            lines.append("")
        else:
            lines.append("- Dynamic histogram: N/A\n")

    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"ok: wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
