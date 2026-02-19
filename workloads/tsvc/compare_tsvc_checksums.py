#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_RE_TSVC_ROW = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(\S+)\s+(\S+)\s*$")


def _read_kernel_list(path: Path | None) -> list[str] | None:
    if path is None:
        return None
    kernels: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        name = raw.strip()
        if not name or name.startswith("#"):
            continue
        kernels.append(name)
    return kernels


def _parse_log(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _RE_TSVC_ROW.match(raw)
        if not m:
            continue
        kernel = m.group(1)
        if kernel == "Loop":
            continue
        if kernel in rows:
            continue
        rows[kernel] = {"time": m.group(2), "checksum": m.group(3)}
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Compare TSVC per-kernel checksum logs (baseline vs candidate)."
    )
    ap.add_argument("--baseline", required=True, help="Baseline TSVC stdout log path")
    ap.add_argument("--candidate", required=True, help="Candidate TSVC stdout log path")
    ap.add_argument("--kernel-list", default=None, help="Optional kernel-list file to constrain comparisons")
    ap.add_argument("--json-out", default=None, help="Optional JSON output path")
    ap.add_argument("--report-out", default=None, help="Optional markdown report output path")
    ap.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Exit non-zero when missing kernels or checksum mismatches are present.",
    )
    args = ap.parse_args(argv)

    baseline = Path(args.baseline)
    candidate = Path(args.candidate)
    kernel_list = Path(args.kernel_list) if args.kernel_list else None
    json_out = Path(args.json_out) if args.json_out else None
    report_out = Path(args.report_out) if args.report_out else None

    if not baseline.exists():
        raise SystemExit(f"error: baseline log not found: {baseline}")
    if not candidate.exists():
        raise SystemExit(f"error: candidate log not found: {candidate}")
    if kernel_list and not kernel_list.exists():
        raise SystemExit(f"error: kernel list not found: {kernel_list}")

    baseline_rows = _parse_log(baseline)
    candidate_rows = _parse_log(candidate)
    kernel_filter = _read_kernel_list(kernel_list)

    if kernel_filter is None:
        kernels = sorted(set(baseline_rows) | set(candidate_rows))
    else:
        kernels = kernel_filter

    missing_in_baseline = [k for k in kernels if k not in baseline_rows]
    missing_in_candidate = [k for k in kernels if k not in candidate_rows]

    mismatches: list[dict[str, str]] = []
    for kernel in kernels:
        b = baseline_rows.get(kernel)
        c = candidate_rows.get(kernel)
        if b is None or c is None:
            continue
        if b["checksum"] != c["checksum"]:
            mismatches.append(
                {
                    "kernel": kernel,
                    "baseline_checksum": b["checksum"],
                    "candidate_checksum": c["checksum"],
                    "baseline_time": b["time"],
                    "candidate_time": c["time"],
                }
            )

    payload = {
        "baseline": str(baseline),
        "candidate": str(candidate),
        "kernel_list": str(kernel_list) if kernel_list else None,
        "kernels_compared": len(kernels),
        "baseline_kernels_found": len(baseline_rows),
        "candidate_kernels_found": len(candidate_rows),
        "missing_in_baseline": missing_in_baseline,
        "missing_in_candidate": missing_in_candidate,
        "checksum_mismatch_count": len(mismatches),
        "checksum_mismatches": mismatches,
        "ok": (not missing_in_baseline and not missing_in_candidate and not mismatches),
    }

    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if report_out:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# TSVC mode checksum comparison",
            "",
            f"- Baseline: `{baseline}`",
            f"- Candidate: `{candidate}`",
            f"- Kernels compared: `{len(kernels)}`",
            f"- Missing in baseline: `{len(missing_in_baseline)}`",
            f"- Missing in candidate: `{len(missing_in_candidate)}`",
            f"- Checksum mismatches: `{len(mismatches)}`",
            f"- Status: `{'PASS' if payload['ok'] else 'FAIL'}`",
        ]
        if missing_in_baseline:
            lines.extend(["", "## Missing In Baseline"])
            lines.extend(f"- `{k}`" for k in missing_in_baseline[:128])
        if missing_in_candidate:
            lines.extend(["", "## Missing In Candidate"])
            lines.extend(f"- `{k}`" for k in missing_in_candidate[:128])
        if mismatches:
            lines.extend(["", "## Checksum Mismatches"])
            for row in mismatches[:128]:
                lines.append(
                    "- `{kernel}` baseline={baseline_checksum} candidate={candidate_checksum}".format(
                        **row
                    )
                )
        report_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.fail_on_mismatch and not payload["ok"]:
        print(
            f"error: checksum comparison failed (missing_baseline={len(missing_in_baseline)} "
            f"missing_candidate={len(missing_in_candidate)} mismatches={len(mismatches)})",
            file=sys.stderr,
        )
        return 2

    print(
        f"ok: checksum comparison kernels={len(kernels)} mismatches={len(mismatches)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
