import argparse
import importlib.util
import json
import os
import pathlib
import sys
import time
import types

from pytest import SkipTest

FORBIDDEN_PREFIXES = ("numpy", "scipy", "pandas", "matplotlib", "petsc4py", "jax", "cupy")


def _load_module(path: pathlib.Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def _iter_test_functions(module: types.ModuleType):
    for name in dir(module):
        if name.startswith("test_"):
            value = getattr(module, name)
            if callable(value):
                yield name, value


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-q", action="store_true")
    parser.add_argument("paths", nargs="*")
    args, _ = parser.parse_known_args()

    root = pathlib.Path.cwd()
    src = root / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))
    paths = [pathlib.Path(path) for path in args.paths] if args.paths else [root / "tests"]

    test_files: list[pathlib.Path] = []
    for path in paths:
        if path.is_dir():
            test_files.extend(sorted(path.rglob("test_*.py")))
        elif path.is_file() and path.name.startswith("test_") and path.suffix == ".py":
            test_files.append(path)

    failures = 0
    skipped = 0
    total = 0
    blocked_imports: list[str] = []
    skip_details: list[dict[str, str]] = []

    if os.environ.get("TOPOPT_BUILD_MODE") == "OFF":
        class ForbiddenFinder:
            def find_spec(self, fullname, path=None, target=None):
                if fullname.startswith(FORBIDDEN_PREFIXES):
                    blocked_imports.append(fullname)
                    raise ImportError(f"Forbidden import in build_off: {fullname}")
                return None

        sys.meta_path.insert(0, ForbiddenFinder())

    start = time.monotonic()
    for test_file in test_files:
        module = _load_module(test_file)
        for name, func in _iter_test_functions(module):
            total += 1
            try:
                func()
            except SkipTest as exc:
                skipped += 1
                reason = str(exc)
                skip_details.append(
                    {
                        "test": f"{test_file}::{name}",
                        "reason": reason,
                    }
                )
            except AssertionError as exc:
                failures += 1
                print(f"FAILED {test_file}::{name} -> {exc}")
            except Exception as exc:
                failures += 1
                print(f"ERROR {test_file}::{name} -> {exc}")

    runtime_s = time.monotonic() - start
    budget_s = float(os.environ.get("TOPOPT_TEST_BUDGET_S", "5"))
    if runtime_s > budget_s:
        failures += 1
        print(f"FAILED runtime budget exceeded: {runtime_s:.2f}s > {budget_s:.2f}s")

    loaded_forbidden = [name for name in sys.modules if name.startswith(FORBIDDEN_PREFIXES)]
    if os.environ.get("TOPOPT_BUILD_MODE") == "OFF" and loaded_forbidden:
        failures += 1
        print(f"FAILED forbidden modules loaded in build_off: {loaded_forbidden}")

    default_cap = "0" if os.environ.get("TOPOPT_BUILD_MODE") == "OFF" else "5"
    skip_cap = int(os.environ.get("TOPOPT_SKIP_CAP", default_cap))
    # Invalid reasons are those missing required documentation keywords.
    # A valid skip reason must contain: "missing" (what's missing), "enable" (how to enable it),
    # and "verified" (impact on VERIFIED status). This ensures skips are documented and justified.
    invalid_reasons = [
        detail
        for detail in skip_details
        if not (
            "missing" in detail["reason"].lower()
            and "enable" in detail["reason"].lower()
            and "verified" in detail["reason"].lower()
        )
    ]
    if invalid_reasons:
        failures += 1
        print("FAILED skip reasons missing required details.")
    # Enforce skip cap against total skip count per REQ-A3-SKIP-003.
    if skipped > skip_cap:
        failures += 1
        print(f"FAILED skip cap exceeded: {skipped} > {skip_cap}")

    if not args.q:
        print(f"collected {total} tests, {failures} failures, {skipped} skipped")

    report_dir = pathlib.Path("ci_out")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "test_report.json").write_text(
        json.dumps(
            {
                "total": total,
                "failures": failures,
                "skipped": skipped,
                "runtime_s": runtime_s,
                "budget_s": budget_s,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (report_dir / "import_audit.json").write_text(
        json.dumps(
            {
                "mode": os.environ.get("TOPOPT_BUILD_MODE", ""),
                "forbidden": list(FORBIDDEN_PREFIXES),
                "detected_imports": sorted(sys.modules.keys()),
                "blocked_imports": blocked_imports,
                "loaded_forbidden": loaded_forbidden,
                "status": "failed" if loaded_forbidden or blocked_imports else "passed",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (report_dir / "skip_report.json").write_text(
        json.dumps(
            {
                "skipped": skipped,
                "cap": skip_cap,
                "status": "failed" if failures else "passed",
                "details": skip_details,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
