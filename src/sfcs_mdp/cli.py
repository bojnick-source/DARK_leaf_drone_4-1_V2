from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from sfcs_mdp.color_qa import ColorProfileScene, evaluate_color_profile_scene
from sfcs_mdp.model import BlockLevel
from sfcs_mdp.runner import package_build, run_traveler, status_build
from sfcs_mdp.validate import SpecValidationError, load_spec, validate_spec


def _parse_block_level(value: str) -> BlockLevel:
    try:
        return BlockLevel(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


DEFAULT_SPEC_PATH = Path("manufacturing/sfcs_drone_mdp_v0.yaml")


def resolve_spec_path(spec_path: Path | None) -> Path:
    if spec_path is None:
        default_path = Path.cwd() / DEFAULT_SPEC_PATH
        if default_path.is_file():
            return default_path
        raise FileNotFoundError(
            f"Spec path not provided and default {DEFAULT_SPEC_PATH.as_posix()} not found."
        )
    resolved = spec_path
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved
    if not resolved.is_file():
        raise FileNotFoundError(f"Spec file not found or unreadable: {resolved}")
    return resolved


def _add_run_args(parser: argparse.ArgumentParser, include_simulate_flag: bool) -> None:
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--rev-tag", required=True)
    parser.add_argument(
        "--block-level",
        type=_parse_block_level,
        default=BlockLevel.BLOCK_0_STRUCTURE_ONLY,
    )
    parser.add_argument("--lot-id")
    parser.add_argument("--ncr-id")
    if include_simulate_flag:
        parser.add_argument("--simulate", action="store_true")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sfcs-mdp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a manufacturing spec")
    validate_parser.add_argument("--spec", type=Path)

    colorqa_parser = subparsers.add_parser("color-qa", help="Evaluate color QA report")
    colorqa_parser.add_argument("--report", type=Path, required=True)

    run_parser = subparsers.add_parser("run", help="Run the traveler")
    _add_run_args(run_parser, include_simulate_flag=True)

    simulate_parser = subparsers.add_parser("simulate", help="Run a simulated traveler")
    _add_run_args(simulate_parser, include_simulate_flag=False)

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
            spec_path = resolve_spec_path(args.spec)
            spec = load_spec(spec_path)
            validate_spec(spec)
        except (SpecValidationError, ValueError) as exc:
            print(f"VALIDATION FAILED: {exc}")
            return 1
        except FileNotFoundError as exc:
            print(str(exc))
            return 1
        print("VALIDATION OK")
        return 0

    if args.command == "color-qa":
        report_path = args.report
        if not report_path.is_absolute():
            report_path = Path.cwd() / report_path
        if not report_path.is_file():
            print(f"QA report not found: {report_path.as_posix()}")
            return 1
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            scene = ColorProfileScene.model_validate(payload)
            report = evaluate_color_profile_scene(scene)
        except (ValueError, ValidationError) as exc:
            print(f"QA REPORT INVALID: {exc}")
            return 1
        print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0

    if args.command == "run":
        try:
            spec_path = resolve_spec_path(args.spec)
            build_dir = run_traveler(
                spec_path=spec_path,
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
        except FileNotFoundError as exc:
            print(str(exc))
            return 1
        if args.simulate:
            print(f"SIMULATION OK: {build_dir.as_posix()}")
        else:
            print(f"RUN OK: {build_dir.as_posix()}")
        return 0

    if args.command == "simulate":
        try:
            spec_path = resolve_spec_path(args.spec)
            build_dir = run_traveler(
                spec_path=spec_path,
                build_id=args.build_id,
                rev_tag=args.rev_tag,
                block_level=args.block_level,
                simulate=True,
                lot_id=args.lot_id,
                ncr_id=args.ncr_id,
            )
        except (SpecValidationError, ValueError, RuntimeError) as exc:
            print(f"SIMULATION FAILED: {exc}")
            return 1
        except FileNotFoundError as exc:
            print(str(exc))
            return 1
        print(f"SIMULATION OK: {build_dir.as_posix()}")
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
