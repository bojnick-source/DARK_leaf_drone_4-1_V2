#!/usr/bin/env python3
"""
Result parsing utilities for v2 engine outputs.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def parse_run_output(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text())
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a run_output.json file.")
    parser.add_argument("run_output", type=Path, help="Path to run_output.json")
    args = parser.parse_args()

    data = parse_run_output(args.run_output)
    json.dump(data, fp=sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
