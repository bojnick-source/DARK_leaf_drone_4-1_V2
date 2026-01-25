#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from engine_ui.resource_locator import ResourceLocator
from engine_ui.schema_validation import summarize_errors, validate_payload_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate engine output JSON against the contract schema.")
    parser.add_argument("payload", type=Path, help="Path to the engine output JSON payload.")
    parser.add_argument(
        "--engine-root",
        type=Path,
        default=None,
        help="Optional engine root override. Defaults to cwd or ENGINE_ROOT.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    locator = ResourceLocator.from_env(default_root=args.engine_root)
    schema_path = locator.schema_path()
    result = validate_payload_file(args.payload, schema_path)
    print(summarize_errors(result.errors))
    if result.missing_fields:
        print("Missing required fields:")
        for field in result.missing_fields:
            print(f"- {field}")
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
