from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from sfcs_mdp.color_qa import ColorProfileScene, evaluate_color_profile_scene
from sfcs_mdp.grading import format_grading_footer
from sfcs_mdp.model import BlockLevel
from sfcs_mdp.runner import package_build, run_traveler, status_build
from sfcs_mdp.validate import SpecValidationError, load_spec, validate_spec
from v2.python.engine import find_engine_cli, run_engine


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
    parser.add_argument(
        "--engine-cli",
        help="Path to v2_engine_cli binary (enables C++ engine integration)",
    )
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

    engine_parser = subparsers.add_parser(
        "engine", help="Run the C++ v2 engine directly"
    )
    engine_parser.add_argument(
        "--engine-cli",
        default=None,
        help="Path to v2_engine_cli binary (auto-detected on PATH if omitted)",
    )
    engine_parser.add_argument(
        "--canonical-input", required=True, help="JSON input string for the engine"
    )
    engine_parser.add_argument(
        "--artifact-root", default=None, help="Override artifact root directory"
    )

    launch_parser = subparsers.add_parser(
        "launch",
        help="Open the Vibe Engineering Studio as a desktop application",
    )
    launch_parser.add_argument(
        "--ui-dir", type=Path, default=None, help="Path to the ui/ directory"
    )
    launch_parser.add_argument(
        "--port", type=int, default=None, help="HTTP port (auto-selected if omitted)"
    )
    launch_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the server without opening a browser window",
    )

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
            print(format_grading_footer())
            return 1
        except FileNotFoundError as exc:
            print(str(exc))
            print(format_grading_footer())
            return 1
        print("VALIDATION OK")
        print(format_grading_footer())
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
                engine_cli=args.engine_cli,
            )
        except (SpecValidationError, ValueError, RuntimeError) as exc:
            print(f"RUN FAILED: {exc}")
            print(format_grading_footer())
            return 1
        except FileNotFoundError as exc:
            print(str(exc))
            print(format_grading_footer())
            return 1
        if args.simulate:
            print(f"SIMULATION OK: {build_dir.as_posix()}")
        else:
            print(f"RUN OK: {build_dir.as_posix()}")
        print(format_grading_footer())
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
                engine_cli=args.engine_cli,
            )
        except (SpecValidationError, ValueError, RuntimeError) as exc:
            print(f"SIMULATION FAILED: {exc}")
            print(format_grading_footer())
            return 1
        except FileNotFoundError as exc:
            print(str(exc))
            print(format_grading_footer())
            return 1
        print(f"SIMULATION OK: {build_dir.as_posix()}")
        print(format_grading_footer())
        return 0

    if args.command == "status":
        try:
            status = status_build(args.build_id)
        except FileNotFoundError as exc:
            print(str(exc))
            print(format_grading_footer())
            return 1
        print(json.dumps(status, indent=2))
        print(format_grading_footer())
        return 0

    if args.command == "package":
        try:
            package_path = package_build(args.build_id)
        except (FileNotFoundError, RuntimeError) as exc:
            print(str(exc))
            print(format_grading_footer())
            return 1
        print(f"PACKAGE OK: {package_path.as_posix()}")
        print(format_grading_footer())
        return 0

    if args.command == "engine":
        cli_path = find_engine_cli(args.engine_cli)
        if cli_path is None:
            print(
                "v2_engine_cli not found. Build the C++ engine first:\n"
                "  cmake -S . -B build -DENABLE_V2_ENGINE=ON\n"
                "  cmake --build build"
            )
            print(format_grading_footer())
            return 1
        try:
            result = run_engine(
                cli_path,
                args.canonical_input,
                artifact_root=args.artifact_root,
            )
        except RuntimeError as exc:
            print(f"ENGINE FAILED: {exc}")
            print(format_grading_footer())
            return 1
        print(json.dumps(result, indent=2, sort_keys=True))
        print(format_grading_footer())
        return 0

    if args.command == "launch":
        from sfcs_mdp.desktop import launch as desktop_launch

        return desktop_launch(
            ui_dir=args.ui_dir,
            port=args.port,
            no_browser=args.no_browser,
        )

    parser.print_help()
    print(format_grading_footer())
    return 1


if __name__ == "__main__":
    sys.exit(main())
