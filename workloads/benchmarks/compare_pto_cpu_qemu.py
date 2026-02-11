#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PTO_SIM_SRC = REPO_ROOT / "workloads" / "benchmarks" / "pto_cpu_sim_gemm_flash.cpp"
GENERATED_ROOT = REPO_ROOT / "workloads" / "generated"
BIN_DIR = GENERATED_ROOT / "bin"
PTO_SIM_BIN = BIN_DIR / "pto_cpu_sim_gemm_flash"
REPORT_PATH = GENERATED_ROOT / "pto_qemu_value_match.md"

PTO_CHECKSUM_RE = re.compile(r"PTO_SIM_(GEMM|FLASH)_CHECKSUM=0x([0-9a-fA-F]+)")
QEMU_CHECKSUM_RE = re.compile(r"QEMU_(GEMM|FLASH)_CHECKSUM=0x([0-9a-fA-F]+)")


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def pick_cxx(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("CXX")
    if env:
        return env
    for name in ("clang++", "g++", "c++"):
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("error: no host C++ compiler found (set --cxx or CXX)")


def compile_pto_sim(cxx: str, pto_repo: Path) -> None:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        cxx,
        "-std=c++23",
        "-O2",
        "-D__CPU_SIM",
        "-I",
        str(pto_repo / "include"),
        str(PTO_SIM_SRC),
        "-o",
        str(PTO_SIM_BIN),
        "-pthread",
    ]
    p = run(cmd, cwd=REPO_ROOT)
    if p.returncode != 0:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        raise SystemExit("error: failed to build PTO CPU sim checksum program")


def parse_checksums(pattern: re.Pattern[str], text: str, prefix: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for match in pattern.finditer(text):
        found[match.group(1).lower()] = int(match.group(2), 16)
    missing = [name for name in ("gemm", "flash") if name not in found]
    if missing:
        raise SystemExit(f"error: missing {prefix} checksum(s): {', '.join(missing)}")
    return found


def run_pto_cpu_demos(pto_repo: Path) -> dict[str, str]:
    demo_results: dict[str, str] = {}
    run_cpu = pto_repo / "tests" / "run_cpu.py"
    for demo, key in (("gemm", "gemm"), ("flash_attn", "flash")):
        p = run([sys.executable, str(run_cpu), "--demo", demo, "--build-type", "Release"], cwd=pto_repo)
        output = p.stdout + p.stderr
        if p.returncode != 0:
            demo_results[key] = "FAIL"
            continue
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        summary = "PASS"
        for line in lines:
            if "max_abs_diff" in line or "checksum(out)" in line or line.startswith("perf:"):
                summary = line
        demo_results[key] = summary
    return demo_results


def run_qemu_tile(clang: str | None, clangxx: str | None, qemu: str | None, timeout: float) -> str:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "tests" / "qemu" / "run_tests.py"),
        "--suite",
        "tile",
        "--timeout",
        str(timeout),
        "-v",
        "--require-test-id",
        "0x000A0004",
        "--require-test-id",
        "0x000A0005",
    ]
    if qemu:
        cmd.extend(["--qemu", qemu])
    env = os.environ.copy()
    if clang:
        env["CLANG"] = clang
    if clangxx:
        env["CLANGXX"] = clangxx

    p = run(cmd, cwd=REPO_ROOT, env=env)
    output = p.stdout + p.stderr
    if p.returncode != 0:
        sys.stderr.write(output)
        raise SystemExit("error: QEMU tile suite failed")
    return output


def write_report(
    *,
    pto_repo: Path,
    cxx: str,
    pto_demo: dict[str, str],
    pto_checksums: dict[str, int],
    qemu_checksums: dict[str, int],
) -> None:
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
    ok = pto_checksums == qemu_checksums
    lines: list[str] = []
    lines.append("# PTO CPU sim vs Linx QEMU value check")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- pto-isa repo: `{pto_repo}`")
    lines.append(f"- host C++ compiler: `{cxx}`")
    lines.append(f"- PTO sim source: `{PTO_SIM_SRC}`")
    lines.append(f"- QEMU suite: `tests/qemu/run_tests.py --suite tile`")
    lines.append("")
    lines.append("## PTO CPU demo status")
    lines.append(f"- gemm: `{pto_demo['gemm']}`")
    lines.append(f"- flash_attn: `{pto_demo['flash']}`")
    lines.append("")
    lines.append("## Checksum comparison")
    lines.append(f"- PTO gemm checksum: `0x{pto_checksums['gemm']:016x}`")
    lines.append(f"- QEMU gemm checksum: `0x{qemu_checksums['gemm']:016x}`")
    lines.append(f"- PTO flash checksum: `0x{pto_checksums['flash']:016x}`")
    lines.append(f"- QEMU flash checksum: `0x{qemu_checksums['flash']:016x}`")
    lines.append(f"- match: `{'PASS' if ok else 'FAIL'}`")
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run PTO CPU sim and verify GEMM/flash values against Linx QEMU.")
    parser.add_argument("--pto-repo", default=str(Path.home() / "pto-isa"), help="Path to pto-isa repository")
    parser.add_argument("--cxx", default=None, help="Host C++ compiler for PTO CPU sim checksum program")
    parser.add_argument("--clang", default=None, help="Path to Linx clang used by QEMU test build")
    parser.add_argument("--clangxx", default=None, help="Path to Linx clang++ used by QEMU test build")
    parser.add_argument("--qemu", default=None, help="Path to qemu-system-linx64")
    parser.add_argument("--timeout", type=float, default=60.0, help="QEMU timeout in seconds")
    args = parser.parse_args(argv)

    pto_repo = Path(os.path.expanduser(args.pto_repo)).resolve()
    if not (pto_repo / "include" / "pto" / "pto-inst.hpp").exists():
        raise SystemExit(f"error: invalid pto-isa repo path: {pto_repo}")

    cxx = pick_cxx(args.cxx)
    compile_pto_sim(cxx, pto_repo)

    pto_demo = run_pto_cpu_demos(pto_repo)

    p = run([str(PTO_SIM_BIN)], cwd=REPO_ROOT)
    if p.returncode != 0:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        raise SystemExit("error: PTO CPU sim checksum program failed")
    pto_text = p.stdout + p.stderr
    pto_checksums = parse_checksums(PTO_CHECKSUM_RE, pto_text, "PTO")

    qemu_text = run_qemu_tile(args.clang, args.clangxx, args.qemu, args.timeout)
    qemu_checksums = parse_checksums(QEMU_CHECKSUM_RE, qemu_text, "QEMU")

    write_report(
        pto_repo=pto_repo,
        cxx=cxx,
        pto_demo=pto_demo,
        pto_checksums=pto_checksums,
        qemu_checksums=qemu_checksums,
    )

    if pto_checksums != qemu_checksums:
        sys.stderr.write("error: PTO/QEMU checksum mismatch\n")
        return 1

    print(f"ok: checksum match (gemm=0x{pto_checksums['gemm']:016x}, flash=0x{pto_checksums['flash']:016x})")
    print(f"ok: report written to {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
