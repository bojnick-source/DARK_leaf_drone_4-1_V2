#!/usr/bin/env python3
"""
Minimal orchestration tool for batching v2 engine runs.

Reads canonical input strings and invokes the v2_engine_cli binary for each,
collecting emitted JSON outputs.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List


def run_single(cli: str, canonical_input: str, artifact_root: str | None = None) -> dict:
    cmd = [cli, "--canonical-input", canonical_input]
    if artifact_root:
        cmd.extend(["--artifact-root", artifact_root])
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def run_batch(cli: str, inputs: Iterable[str], artifact_root: str | None = None) -> List[dict]:
    outputs: List[dict] = []
    for canonical_input in inputs:
        outputs.append(run_single(cli, canonical_input, artifact_root))
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch runner for v2 engine CLI.")
    parser.add_argument("--cli", default="v2_engine_cli", help="Path to v2_engine_cli executable")
    parser.add_argument("--inputs-file", type=Path, help="File containing one canonical input per line")
    parser.add_argument("--canonical-input", action="append", help="Inline canonical input string")
    parser.add_argument("--artifact-root", help="Override artifact root for all runs")
    args = parser.parse_args()

    inputs: List[str] = []
    if args.inputs_file:
        inputs.extend([line.strip() for line in args.inputs_file.read_text().splitlines() if line.strip()])
    if args.canonical_input:
        inputs.extend(args.canonical_input)

    if not inputs:
        parser.error("provide at least one canonical input via --inputs-file or --canonical-input")

    outputs = run_batch(args.cli, inputs, args.artifact_root)
    json.dump(outputs, fp=sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
