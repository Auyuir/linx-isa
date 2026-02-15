#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = REPO_ROOT / "workloads"
GENERATED_DIR = REPO_ROOT / "workloads" / "generated"


@dataclass(frozen=True)
class StepResult:
    name: str
    command: list[str]
    return_code: int


def _run(cmd: list[str], *, verbose: bool = False) -> subprocess.CompletedProcess[bytes]:
    if verbose:
        print("+", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
    return subprocess.run(cmd, cwd=str(REPO_ROOT), check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _resolve_cc(arg_cc: str | None) -> str:
    cc = arg_cc or os.environ.get("CC")
    if not cc:
        raise SystemExit("error: compiler is required; set --cc or CC")
    return cc


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Run benchmark portfolio (CoreMark/Dhrystone + optional PolyBench/ctuning).")
    ap.add_argument("--cc", default=None, help="Compiler path (or set CC)")
    ap.add_argument("--target", required=True, help="Target triple")
    ap.add_argument("--sysroot", default=None, help="Optional sysroot")
    ap.add_argument("--run-command", default=None, help="Optional runtime wrapper command (supports {exe})")
    ap.add_argument("--polybench", action="store_true", help="Include PolyBench kernels")
    ap.add_argument("--polybench-kernels", default="gemm,jacobi-2d")
    ap.add_argument("--ctuning-root", default=str(Path.home() / "ctuning-programs"))
    ap.add_argument("--ctuning-limit", type=int, default=0, help="Codelet count (0 disables ctuning)")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    cc = _resolve_cc(args.cc)
    results: list[StepResult] = []

    run_bench_cmd = [
        sys.executable,
        str(BENCH_DIR / "run_benchmarks.py"),
        "--cc",
        cc,
        "--target",
        args.target,
    ]
    if args.sysroot:
        run_bench_cmd += ["--sysroot", args.sysroot]
    if args.run_command:
        run_bench_cmd += ["--run-command", args.run_command]
    if args.verbose:
        run_bench_cmd.append("--verbose")

    p = _run(run_bench_cmd, verbose=args.verbose)
    sys.stdout.buffer.write(p.stdout)
    sys.stderr.buffer.write(p.stderr)
    results.append(StepResult(name="coremark+dhrystone", command=run_bench_cmd, return_code=p.returncode))
    if p.returncode != 0:
        raise SystemExit("error: run_benchmarks.py failed")

    if args.polybench:
        run_poly_cmd = [
            sys.executable,
            str(BENCH_DIR / "run_polybench.py"),
            "--cc",
            cc,
            "--target",
            args.target,
            "--kernels",
            args.polybench_kernels,
        ]
        if args.sysroot:
            run_poly_cmd += ["--sysroot", args.sysroot]
        if args.run_command:
            run_poly_cmd += ["--run-command", args.run_command]
        if args.verbose:
            run_poly_cmd.append("--verbose")

        p = _run(run_poly_cmd, verbose=args.verbose)
        sys.stdout.buffer.write(p.stdout)
        sys.stderr.buffer.write(p.stderr)
        results.append(StepResult(name="polybench", command=run_poly_cmd, return_code=p.returncode))
        if p.returncode != 0:
            raise SystemExit("error: run_polybench.py failed")

    if args.ctuning_limit > 0:
        ctuning_root = Path(os.path.expanduser(args.ctuning_root))
        if not (ctuning_root / "program").exists():
            print(f"note: skipping ctuning; root not found: {ctuning_root}")
        elif "clang" not in Path(cc).name:
            print("note: skipping ctuning; --cc is not clang, and ctuning runner requires clang/ld.lld")
        else:
            clang = cc
            lld = str(Path(cc).parent / "ld.lld")
            qemu = os.environ.get("QEMU")
            ct_cmd = [
                sys.executable,
                str(BENCH_DIR / "ctuning" / "run_milepost_codelets.py"),
                "--ctuning-root",
                str(ctuning_root),
                "--target",
                args.target,
                "--clang",
                clang,
                "--lld",
                lld,
                "--limit",
                str(args.ctuning_limit),
                "--compile-only",
            ]
            if qemu and args.run_command:
                # Allow explicit run by setting --run-command and QEMU env together.
                ct_cmd = [c for c in ct_cmd if c != "--compile-only"]
                ct_cmd += ["--run", "--qemu", qemu]
            if args.verbose:
                ct_cmd.append("--verbose")

            p = _run(ct_cmd, verbose=args.verbose)
            sys.stdout.buffer.write(p.stdout)
            sys.stderr.buffer.write(p.stderr)
            results.append(StepResult(name="ctuning", command=ct_cmd, return_code=p.returncode))
            if p.returncode != 0:
                raise SystemExit("error: ctuning runner failed")

    report = GENERATED_DIR / "portfolio_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Benchmark Portfolio Report", "", "| Step | Exit | Command |", "|---|---:|---|"]
    for r in results:
        cmd = " ".join(shlex.quote(c) for c in r.command)
        lines.append(f"| `{r.name}` | {r.return_code} | `{cmd}` |")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ok: wrote {report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
