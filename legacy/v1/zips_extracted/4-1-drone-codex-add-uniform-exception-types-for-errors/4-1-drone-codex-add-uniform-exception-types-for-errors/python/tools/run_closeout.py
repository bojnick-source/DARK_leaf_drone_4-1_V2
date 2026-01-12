# ============================================================================
# Fragment 1.4.29 — Python Runner Wrapper (Call CLI + Manage Paths)
# File: python/tools/run_closeout.py
# ============================================================================
#
# Purpose:
# - Lightweight wrapper to invoke closeout_cli consistently from scripts/CI.
# - Handles locating the binary, forwarding args, and stable exit codes.
#
# Notes:
# - No repo-specific config parsing yet (kept minimal on purpose).
#
# ============================================================================

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from typing import List, Optional


def _find_closeout_cli(explicit: Optional[str]) -> str:
    if explicit:
        # Validate explicit path exists and is executable
        if not os.path.isfile(explicit):
            raise FileNotFoundError(f"Specified binary does not exist: {explicit}")
        if not os.access(explicit, os.X_OK):
            raise PermissionError(f"Specified binary is not executable: {explicit}")
        return explicit

    # 1) PATH
    p = shutil.which("closeout_cli")
    if p:
        return p

    # 2) Common local build locations (best-effort)
    candidates = [
        os.path.join("build", "closeout_cli"),
        os.path.join("build", "cpp", "tools", "closeout_cli"),
        os.path.join("build", "bin", "closeout_cli"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return os.path.abspath(c)

    raise FileNotFoundError(
        "Could not locate closeout_cli. Provide --bin PATH or ensure it is on PATH."
    )


def _run(cmd: List[str]) -> int:
    proc = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    return int(proc.returncode)


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="run_closeout.py")
    ap.add_argument("--bin", default=None, help="Path to closeout_cli binary (optional).")
    ap.add_argument("--strict", action="store_true", help="Use strict default thresholds.")
    ap.add_argument("--dry-run", action="store_true", help="Validate + write headers only.")
    ap.add_argument("--out-evidence", default="", help="Evidence CSV output path.")
    ap.add_argument("--out-gates", default="", help="Gates CSV output path.")

    args = ap.parse_args(argv)

    try:
        bin_path = _find_closeout_cli(args.bin)
    except Exception as e:
        print(f"run_closeout error: {e}", file=sys.stderr)
        return 2

    cmd: List[str] = [bin_path]
    if args.strict:
        cmd.append("--strict")
    if args.dry_run:
        cmd.append("--dry-run")
    if args.out_evidence:
        cmd += ["--out-evidence", args.out_evidence]
    if args.out_gates:
        cmd += ["--out-gates", args.out_gates]

    try:
        return _run(cmd)
    except FileNotFoundError as e:
        print(f"run_closeout error: {e}", file=sys.stderr)
        return 2
    except subprocess.SubprocessError as e:
        print(f"run_closeout subprocess error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
