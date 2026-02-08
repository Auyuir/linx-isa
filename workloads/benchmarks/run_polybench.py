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


BENCH_DIR = Path(__file__).resolve().parent
WORKLOADS_DIR = BENCH_DIR.parent
REPO_ROOT = WORKLOADS_DIR.parent

LIBC_DIR = REPO_ROOT / "toolchain" / "libc"
LIBC_INCLUDE = LIBC_DIR / "include"
LIBC_SRC = LIBC_DIR / "src"

POLYBENCH_DIR = BENCH_DIR / "third_party" / "PolyBenchC"
POLYBENCH_UTIL = POLYBENCH_DIR / "utilities"
POLYBENCH_LINX = BENCH_DIR / "polybench" / "linx"

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
    if cand.exists():
        return cand
    if cand_tci.exists():
        return cand_tci
    return None


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
    if not path.exists():
        return None, None
    try:
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


def _build_runtime_objects(clang: Path, target: str, out_dir: Path, *, verbose: bool) -> list[Path]:
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

    def cc(src: Path, obj_name: str) -> Path:
        obj = rt_dir / obj_name
        cmd = [str(clang), *cflags_base, "-c", str(src), "-o", str(obj)]
        p = _run(cmd, verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            sys.stderr.buffer.write(p.stderr)
            raise SystemExit(f"error: runtime compile failed: {src}")
        return obj

    return [
        cc(BENCH_DIR / "common" / "startup.c", "startup.o"),
        cc(LIBC_SRC / "syscall.c", "syscall.o"),
        cc(LIBC_SRC / "stdio" / "stdio.c", "stdio.o"),
        cc(LIBC_SRC / "stdlib" / "stdlib.c", "stdlib.o"),
        cc(LIBC_SRC / "string" / "mem.c", "mem.o"),
        cc(LIBC_SRC / "string" / "str.c", "str.o"),
        cc(LIBC_SRC / "math" / "math.c", "math.o"),
    ]


@dataclass(frozen=True)
class Result:
    name: str
    elf: Path
    objdump: Path
    qemu_stdout: Path
    qemu_stderr: Path
    dyn_hist: Path | None
    static_insns: int
    dyn_insns_qemu: int | None
    dyn_insns_plugin: int | None


def _build_and_run_one(
    *,
    name: str,
    src: Path,
    include_dirs: list[Path],
    clang: Path,
    lld: Path,
    llvm_objdump: Path,
    llvm_objcopy: Path,
    qemu: Path,
    target: str,
    runtime_objs: list[Path],
    out_dir: Path,
    artifacts_dir: Path,
    verbose: bool,
    timeout_s: float,
    dynamic_hist: bool,
) -> Result:
    build_dir = out_dir / "polybench" / name
    build_dir.mkdir(parents=True, exist_ok=True)

    wrapper = build_dir / "main_wrap.c"
    wrapper.write_text(
        "\n".join(
            [
                "extern int polybench_main(int argc, char **argv);",
                "int main(void) {",
                '  static char arg0[] = "linx";',
                "  static char *argv[] = { arg0, 0 };",
                "  return polybench_main(1, argv);",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    obj_kernel = build_dir / "kernel.o"
    obj_wrap = build_dir / "wrap.o"
    obj_poly = build_dir / "polybench_linx.o"

    cflags = [
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
        "-std=gnu99",
        "-DMINI_DATASET",
        f"-I{LIBC_INCLUDE}",
        f"-I{POLYBENCH_UTIL}",
        *[f"-I{p}" for p in include_dirs],
        "-Dmain=polybench_main",
    ]

    p = _run([str(clang), *cflags, "-c", str(src), "-o", str(obj_kernel)], verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"error: compile failed: {src}")

    wrap_flags = [f for f in cflags if f != "-Dmain=polybench_main"]
    p = _run([str(clang), *wrap_flags, "-c", str(wrapper), "-o", str(obj_wrap)], verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"error: compile failed: {wrapper}")

    p = _run([str(clang), *wrap_flags, "-c", str(POLYBENCH_LINX / "polybench_linx.c"), "-o", str(obj_poly)], verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit("error: compile failed: polybench_linx.c")

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    elf_dir = artifacts_dir / "elf"
    bin_dir = artifacts_dir / "bin"
    objdump_dir = artifacts_dir / "objdump" / "polybench"
    qemu_dir = artifacts_dir / "qemu"
    elf_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    objdump_dir.mkdir(parents=True, exist_ok=True)
    qemu_dir.mkdir(parents=True, exist_ok=True)

    elf = elf_dir / f"polybench_{name}.elf"
    link_cmd = [str(lld), "--entry=_start", "-o", str(elf), *[str(o) for o in runtime_objs], str(obj_poly), str(obj_wrap), str(obj_kernel)]
    p = _run(link_cmd, verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"error: link failed: {name}")

    objdump_path = objdump_dir / f"{name}.objdump.txt"
    p = _run([str(llvm_objdump), "-d", f"--triple={target}", str(elf)], verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"error: llvm-objdump failed: {name}")
    objdump_path.write_bytes(p.stdout)

    bin_path = bin_dir / f"polybench_{name}.bin"
    p = _run([str(llvm_objcopy), "--only-section=.text", "-O", "binary", str(elf), str(bin_path)], verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"error: llvm-objcopy failed: {name}")

    qemu_stdout = qemu_dir / f"polybench_{name}.stdout.txt"
    qemu_stderr = qemu_dir / f"polybench_{name}.stderr.txt"
    dyn_hist_path = qemu_dir / f"polybench_{name}.dyn_insn_hist.json" if dynamic_hist else None

    qemu_cmd = [
        str(qemu),
        "-M",
        "virt",
        "-nographic",
        "-monitor",
        "none",
        "-kernel",
        str(elf),
    ]
    if dynamic_hist:
        plugin = os.environ.get("LINX_INSN_HIST_PLUGIN")
        if not plugin:
            raise SystemExit("error: --dynamic-hist requires LINX_INSN_HIST_PLUGIN=/path/to/liblinx_insn_hist.so")
        qemu_cmd += ["-plugin", f"{plugin},out={dyn_hist_path},top=200"]

    p = _run(qemu_cmd, verbose=verbose, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_s)
    qemu_stdout.write_bytes(p.stdout or b"")
    qemu_stderr.write_bytes(p.stderr or b"")

    if p.returncode != 0:
        raise SystemExit(f"error: QEMU failed: {name} (exit={p.returncode})\n  stdout: {qemu_stdout}\n  stderr: {qemu_stderr}")

    static_insns, _, _ = _parse_objdump(objdump_path)
    dyn_qemu = _parse_linx_insn_count(p.stdout or b"", p.stderr or b"")
    dyn_plugin = None
    if dyn_hist_path:
        dyn_plugin, _ = _load_dyn_hist(dyn_hist_path)

    return Result(
        name=f"polybench:{name}",
        elf=elf,
        objdump=objdump_path,
        qemu_stdout=qemu_stdout,
        qemu_stderr=qemu_stderr,
        dyn_hist=dyn_hist_path,
        static_insns=static_insns,
        dyn_insns_qemu=dyn_qemu,
        dyn_insns_plugin=dyn_plugin,
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build + run a small PolyBench/C subset on LinxISA QEMU.")
    ap.add_argument("--clang", default=None, help="Path to clang (env: CLANG)")
    ap.add_argument("--lld", default=None, help="Path to ld.lld (env: LLD)")
    ap.add_argument("--qemu", default=None, help="Path to qemu-system-linx64 (env: QEMU)")
    ap.add_argument("--target", default="linx64-linx-none-elf", help="Target triple")
    ap.add_argument("--timeout", type=float, default=60.0, help="QEMU timeout (seconds)")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose build/run commands")
    ap.add_argument("--dynamic-hist", action="store_true", help="Enable dynamic per-mnemonic histogram via QEMU plugin.")
    ap.add_argument(
        "--kernels",
        default="gemm,jacobi-2d",
        help="Comma-separated PolyBench kernels to run (default: gemm,jacobi-2d)",
    )
    args = ap.parse_args(argv)

    if not POLYBENCH_DIR.exists():
        raise SystemExit(f"error: PolyBenchC not found at {POLYBENCH_DIR} (run workloads/benchmarks/fetch_third_party.sh)")
    if not POLYBENCH_LINX.exists():
        raise SystemExit(f"error: missing Linx PolyBench port layer: {POLYBENCH_LINX}")

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

    runtime_objs = _build_runtime_objects(clang, args.target, out_dir, verbose=args.verbose)

    kernels = [k.strip() for k in args.kernels.split(",") if k.strip()]
    if not kernels:
        raise SystemExit("error: --kernels was empty")

    # Map kernel name -> (source, include_dirs).
    kernel_db: dict[str, tuple[Path, list[Path]]] = {
        "gemm": (
            POLYBENCH_DIR / "linear-algebra" / "blas" / "gemm" / "gemm.c",
            [POLYBENCH_DIR / "linear-algebra" / "blas" / "gemm"],
        ),
        "jacobi-2d": (
            POLYBENCH_DIR / "stencils" / "jacobi-2d" / "jacobi-2d.c",
            [POLYBENCH_DIR / "stencils" / "jacobi-2d"],
        ),
    }

    results: list[Result] = []
    for k in kernels:
        if k not in kernel_db:
            raise SystemExit(f"error: unknown kernel: {k} (known: {', '.join(sorted(kernel_db.keys()))})")
        src, inc = kernel_db[k]
        if not src.exists():
            raise SystemExit(f"error: kernel source missing: {src}")
        results.append(
            _build_and_run_one(
                name=k,
                src=src,
                include_dirs=inc,
                clang=clang,
                lld=lld,
                llvm_objdump=llvm_objdump,
                llvm_objcopy=llvm_objcopy,
                qemu=qemu,
                target=args.target,
                runtime_objs=runtime_objs,
                out_dir=out_dir,
                artifacts_dir=generated_dir,
                verbose=args.verbose,
                timeout_s=args.timeout,
                dynamic_hist=args.dynamic_hist,
            )
        )

    # Print a compact summary for logs; detailed stats live in workloads/generated/.
    for r in results:
        dyn = r.dyn_insns_plugin if r.dyn_insns_plugin is not None else r.dyn_insns_qemu
        print(f"ok: {r.name}: static={r.static_insns} dynamic={dyn} objdump={r.objdump}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
