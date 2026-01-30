#!/usr/bin/env python3
"""
Result parsing utilities for v2 engine outputs.
"""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a run_output.json file.")
    parser.add_argument("run_output", type=Path, help="Path to run_output.json")
    args = parser.parse_args()

    data = json.loads(args.run_output.read_text())
    json.dump(data, fp=sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
