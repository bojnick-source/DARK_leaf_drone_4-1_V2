from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sfcs_mdp.model import BlockLevel
from sfcs_mdp.runner import package_build, run_traveler, status_build
from sfcs_mdp.validate import SpecValidationError, load_spec, validate_spec


def _parse_block_level(value: str) -> BlockLevel:
    try:
        return BlockLevel(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sfcs-mdp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a manufacturing spec")
    validate_parser.add_argument("--spec", required=True, type=Path)

    run_parser = subparsers.add_parser("run", help="Run the traveler")
    run_parser.add_argument("--spec", required=True, type=Path)
    run_parser.add_argument("--build-id", required=True)
    run_parser.add_argument("--rev-tag", required=True)
    run_parser.add_argument(
        "--block-level",
        type=_parse_block_level,
        default=BlockLevel.BLOCK_0_STRUCTURE_ONLY,
    )
    run_parser.add_argument("--simulate", action="store_true")
    run_parser.add_argument("--lot-id")
    run_parser.add_argument("--ncr-id")

    status_parser = subparsers.add_parser("status", help="Show build status")
    status_parser.add_argument("--build-id", required=True)

    package_parser = subparsers.add_parser("package", help="Package acceptance data")
    package_parser.add_argument("--build-id", required=True)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "validate":
        try:
            spec = load_spec(args.spec)
            validate_spec(spec)
        except (SpecValidationError, ValueError) as exc:
            print(f"VALIDATION FAILED: {exc}")
            return 1
        print("VALIDATION OK")
        return 0

    if args.command == "run":
        try:
            build_dir = run_traveler(
                spec_path=args.spec,
                build_id=args.build_id,
                rev_tag=args.rev_tag,
                block_level=args.block_level,
                simulate=args.simulate,
                lot_id=args.lot_id,
                ncr_id=args.ncr_id,
            )
        except (SpecValidationError, ValueError, RuntimeError) as exc:
            print(f"RUN FAILED: {exc}")
            return 1
        print(f"RUN OK: {build_dir.as_posix()}")
        return 0

    if args.command == "status":
        try:
            status = status_build(args.build_id)
        except FileNotFoundError as exc:
            print(str(exc))
            return 1
        print(json.dumps(status, indent=2))
        return 0

    if args.command == "package":
        try:
            package_path = package_build(args.build_id)
        except (FileNotFoundError, RuntimeError) as exc:
            print(str(exc))
            return 1
        print(f"PACKAGE OK: {package_path.as_posix()}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
