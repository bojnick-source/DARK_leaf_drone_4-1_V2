#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import sys
from importlib.util import find_spec


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--status", required=True, choices=["passed", "failed"])
    parser.add_argument("--repro", required=True)
    parser.add_argument("--numpy-active", action="store_true")
    args = parser.parse_args()

    report = {
        "mode": args.mode,
        "status": args.status,
        "numpy_available": find_spec("numpy") is not None,
        "numpy_active": args.numpy_active,
        "python_version": sys.version,
        "repro_command": args.repro,
        "env": {
            "TOPOPT_BUILD_MODE": os.environ.get("TOPOPT_BUILD_MODE", ""),
            "PIP_NO_INDEX": os.environ.get("PIP_NO_INDEX", ""),
            "PIP_DISABLE_PIP_VERSION_CHECK": os.environ.get("PIP_DISABLE_PIP_VERSION_CHECK", ""),
            "PIP_DEFAULT_TIMEOUT": os.environ.get("PIP_DEFAULT_TIMEOUT", ""),
        },
    }

    output = pathlib.Path("ci_out") / "build_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
