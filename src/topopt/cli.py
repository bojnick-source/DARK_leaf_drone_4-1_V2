from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime
from typing import Any

from importlib import import_module
from importlib.util import find_spec

from topopt.core.robust import robust_summary
from topopt.uq.lhs import VariableSpec, batch_samples, generate_lhs
from topopt.viz import generate_viz

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_schema(data: dict[str, Any], schema_path: pathlib.Path) -> None:
    schema = _load_json(schema_path)
    if find_spec("jsonschema") is None:
        raise RuntimeError("jsonschema is required for validation but is not installed.")
    Draft202012Validator = import_module("jsonschema").Draft202012Validator
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        message = "\n".join([f"{error.message}" for error in errors])
        raise ValueError(message)


def _default_variables() -> list[VariableSpec]:
    return [
        VariableSpec("length", "uniform", {"low": 0.5, "high": 2.0}),
        VariableSpec("height", "uniform", {"low": 0.2, "high": 0.6}),
        VariableSpec("tip_force", "lognormal", {"mean": 6.9, "sigma": 0.2}),
        VariableSpec("youngs_modulus", "normal", {"mean": 2.1e11, "std": 1.0e10}),
        VariableSpec("material_class", "uniform", {"low": 0.0, "high": 1.0}, choices=["steel", "aluminum"]),
    ]


def _write_parquet(samples: dict[str, list[float]], output: pathlib.Path) -> None:
    if find_spec("pyarrow") is None:
        raise RuntimeError("pyarrow is required for parquet output but is not installed.")
    pa = import_module("pyarrow")
    pq = import_module("pyarrow.parquet")
    table = pa.table({key: pa.array(value) for key, value in samples.items()})
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output)


def _run_script(script: str, *args: str) -> int:
    cmd = [sys.executable, str(ROOT / script), *args]
    return subprocess.call(cmd)


def _run_shell(script_path: pathlib.Path) -> int:
    return subprocess.call(["bash", str(script_path)])


def cmd_validate(args: argparse.Namespace) -> int:
    config_path = pathlib.Path(args.config)
    config = _load_json(config_path)
    _validate_schema(config, ROOT / "schemas" / "config.schema.json")
    print("Config validation passed.")
    return 0


def cmd_uq_sample(args: argparse.Namespace) -> int:
    variables = _default_variables()
    result = generate_lhs(
        n=args.n,
        variables=variables,
        seed=args.seed,
        maximin=not args.no_maximin,
        attempts=args.attempts,
        corr_weight=args.corr_weight,
    )
    _write_parquet(result["samples"], pathlib.Path(args.out))
    metrics_path = pathlib.Path(args.out).with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(result["metrics"], indent=2), encoding="utf-8")
    print(f"Wrote samples to {args.out}")
    return 0


def _run_benchmark(benchmark_id: str, config_path: pathlib.Path) -> dict[str, Any]:
    config = _load_json(config_path)
    _validate_schema(config, ROOT / "schemas" / "config.schema.json")
    defaults = config.get("defaults", {})
    uq_defaults = defaults.get("uq", {})
    n_samples = int(uq_defaults.get("lhs_samples", {}).get("value", 16))
    seed = int(uq_defaults.get("lhs_seed", {}).get("value", 42))
    parallel_workers = int(defaults.get("solver", {}).get("parallel_workers", {}).get("value", 2))

    variables = _default_variables()
    lhs = generate_lhs(n=n_samples, variables=variables, seed=seed, maximin=True, attempts=25)
    samples = lhs["samples"]
    unit_samples = lhs["unit_samples"]
    batches = batch_samples(samples, batch_size=max(1, n_samples // 4))

    robust = robust_summary(samples, unit_samples, variables, benchmark_id, parallel_workers)

    run_id = f"{benchmark_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    projection = [row[:2] for row in unit_samples] if unit_samples and len(unit_samples[0]) >= 2 else []
    uq_payload = {
        "lhs_enabled": True,
        "n_samples": n_samples,
        "seed": seed,
        "batching_mode": lhs["batching_mode"],
        "lhs_metrics": lhs["metrics"],
        "robust_history": [robust["primary"]["objective"]],
        "projection": projection,
        "batches": [list(batch.keys()) for batch in batches],
    }

    results = {
        "run_id": run_id,
        "benchmark": benchmark_id,
        "status": "COMPLETED",
        "objectives": robust,
        "uq": uq_payload,
        "artifacts": ["results.json"],
        "notes": "Analytic proxy solver used for CI-small run.",
    }
    (run_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "artifacts": [
            {"path": "results.json", "description": "Run results"},
            {"path": "lhs_metrics.json", "description": "LHS quality metrics"},
        ],
    }
    (run_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "lhs_metrics.json").write_text(json.dumps(lhs["metrics"], indent=2), encoding="utf-8")
    return {"run_id": run_id, "run_dir": run_dir}


def cmd_bench(args: argparse.Namespace) -> int:
    run = _run_benchmark(args.benchmark, pathlib.Path(args.config))
    print(f"Run completed: {run['run_id']}")
    return 0


def cmd_certify(args: argparse.Namespace) -> int:
    run_dir = ROOT / "runs" / args.run_id
    results_path = run_dir / "results.json"
    results = _load_json(results_path)
    uq = results.get("uq", {})
    metrics = uq.get("lhs_metrics", {})

    min_dist = metrics.get("min_pairwise_distance", 0.0)
    max_corr = metrics.get("max_abs_correlation", 1.0)
    thresholds = {"min_pairwise_distance": 0.02, "max_abs_correlation": 0.9}

    uq_verdict = "VERIFIED"
    notes = []
    if min_dist < thresholds["min_pairwise_distance"] or max_corr > thresholds["max_abs_correlation"]:
        uq_verdict = "NOT_VERIFIED"
        notes.append("LHS quality thresholds violated; review sampling strategy.")

    overall_status = "VERIFIED" if uq_verdict == "VERIFIED" else "NOT_VERIFIED"

    certificate = {
        "run_id": results["run_id"],
        "overall_status": overall_status,
        "lhs_enabled": True,
        "n_samples": uq.get("n_samples"),
        "seed": uq.get("seed"),
        "batching_mode": uq.get("batching_mode"),
        "lhs_quality_metrics": metrics,
        "uq_mode_verdict": uq_verdict,
        "notes": notes,
    }

    cert_path = run_dir / "results_certificate.json"
    cert_path.write_text(json.dumps(certificate, indent=2), encoding="utf-8")
    print(f"Wrote certificate to {cert_path}")
    return 0


def cmd_viz(args: argparse.Namespace) -> int:
    run_dir = ROOT / "runs" / args.run_id
    results_path = run_dir / "results.json"
    output_path = ROOT / "docs" / "viz" / "index.html"
    generate_viz(results_path, output_path)
    print(f"Wrote viz to {output_path}")
    return 0


def cmd_traceability(_: argparse.Namespace) -> int:
    return _run_script("scripts/traceability_check.py")


def cmd_repo_check(_: argparse.Namespace) -> int:
    required_paths = [
        ROOT / "docs" / "spec_prompt.txt",
        ROOT / "docs" / "requirements.md",
        ROOT / "docs" / "traceability.md",
        ROOT / "docs" / "offline_ci.md",
        ROOT / "docs" / "offline_ci_hardening.md",
        ROOT / "docs" / "ci_artifacts.md",
        ROOT / "schemas" / "config.schema.json",
        ROOT / "schemas" / "results.schema.json",
        ROOT / "schemas" / "artifact.schema.json",
        ROOT / "schemas" / "certificate.schema.json",
        ROOT / "schemas" / "ci" / "build_report.schema.json",
        ROOT / "schemas" / "ci" / "test_report.schema.json",
        ROOT / "schemas" / "ci" / "import_audit.schema.json",
        ROOT / "schemas" / "ci" / "perf_report.schema.json",
        ROOT / "schemas" / "ci" / "skip_report.schema.json",
        ROOT / "schemas" / "ci" / "repo_check.schema.json",
        ROOT / "scripts" / "ci_artifact_check.py",
        ROOT / "scripts" / "no_network_sentinel.py",
    ]
    checks = []
    for path in required_paths:
        if not path.exists():
            print(f"Missing required file: {path}")
            checks.append({"path": str(path), "status": "missing"})
            _write_repo_check("failed", checks)
            return 1
        if path.suffix == ".json":
            try:
                _load_json(path)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON: {path} -> {exc}")
                checks.append({"path": str(path), "status": "invalid_json"})
                _write_repo_check("failed", checks)
                return 1
        checks.append({"path": str(path), "status": "ok"})

    help_status = subprocess.call([sys.executable, "-m", "topopt.cli", "--help"])
    if help_status != 0:
        print("CLI help command failed.")
        checks.append({"check": "cli_help", "status": "failed"})
        _write_repo_check("failed", checks)
        return help_status
    checks.append({"check": "cli_help", "status": "ok"})

    off_result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,importlib; os.environ['TOPOPT_BUILD_MODE']='OFF';"
            "importlib.import_module('topopt.optional_heavy')",
        ],
        capture_output=True,
        text=True,
    )
    if off_result.returncode == 0:
        print("build_off should block optional_heavy imports.")
        checks.append({"check": "build_off_optional_heavy", "status": "failed"})
        _write_repo_check("failed", checks)
        return 1
    checks.append({"check": "build_off_optional_heavy", "status": "ok"})

    on_result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,importlib; os.environ['TOPOPT_BUILD_MODE']='ON';"
            "importlib.import_module('topopt.optional_heavy')",
        ]
        ,
        capture_output=True,
        text=True,
    )
    if on_result.returncode != 0:
        print("build_on failed to import optional_heavy.")
        if on_result.stderr:
            print(on_result.stderr.strip())
        checks.append({"check": "build_on_optional_heavy", "status": "failed"})
        _write_repo_check("failed", checks)
        return on_result.returncode
    checks.append({"check": "build_on_optional_heavy", "status": "ok"})

    status = _run_script("scripts/prompt_must_id_check.py")
    if status != 0:
        checks.append({"check": "prompt_must_id_check", "status": "failed"})
        _write_repo_check("failed", checks)
        return status
    checks.append({"check": "prompt_must_id_check", "status": "ok"})
    trace_status = _run_script("scripts/traceability_check.py")
    if trace_status != 0:
        checks.append({"check": "traceability_check", "status": "failed"})
        _write_repo_check("failed", checks)
        return trace_status
    checks.append({"check": "traceability_check", "status": "ok"})
    _write_repo_check("passed", checks)
    return 0


def _write_repo_check(status: str, checks: list[dict[str, str]]) -> None:
    report = {"status": status, "checks": checks}
    output = ROOT / "ci_out" / "repo_check.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")


def cmd_build_verify(_: argparse.Namespace) -> int:
    on_status = _run_shell(ROOT / "ci" / "build_on.sh")
    off_status = _run_shell(ROOT / "ci" / "build_off.sh")
    return max(on_status, off_status)


def cmd_ci_verify(_: argparse.Namespace) -> int:
    status = cmd_repo_check(argparse.Namespace())
    if status != 0:
        return status
    test_status = subprocess.call([sys.executable, "-m", "pytest", "tests/topopt"])
    if test_status != 0:
        return test_status
    return cmd_build_verify(argparse.Namespace())


def cmd_lint(args: argparse.Namespace) -> int:
    ruff_available = find_spec("ruff") is not None
    mypy_available = find_spec("mypy") is not None
    if not (ruff_available and mypy_available):
        print("Lint dependencies missing: ruff/mypy.")
        return 1
    if args.fix:
        ruff_format = subprocess.call([sys.executable, "-m", "ruff", "format", "src", "tests", "scripts"])
        ruff_fix = subprocess.call([sys.executable, "-m", "ruff", "check", "--fix", "src", "tests", "scripts"])
        return max(ruff_format, ruff_fix)
    ruff_format = subprocess.call([sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "scripts"])
    ruff = subprocess.call([sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"])
    mypy = subprocess.call([sys.executable, "-m", "mypy", "src/topopt"])
    return max(ruff_format, ruff, mypy)


def cmd_list_runs(_: argparse.Namespace) -> int:
    runs = sorted((ROOT / "runs").glob("*") )
    for run in runs:
        if run.is_dir():
            print(run.name)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    left = _load_json(ROOT / "runs" / args.left / "results.json")
    right = _load_json(ROOT / "runs" / args.right / "results.json")
    diff = {
        "left": left.get("objectives", {}),
        "right": right.get("objectives", {}),
    }
    print(json.dumps(diff, indent=2))
    return 0


def cmd_diff_config(args: argparse.Namespace) -> int:
    left = _load_json(pathlib.Path(args.left))
    right = _load_json(pathlib.Path(args.right))
    print(json.dumps({"left": left, "right": right}, indent=2))
    return 0


def cmd_diagnose(_: argparse.Namespace) -> int:
    print("Run 'topopt repo-check' and review runs/traceability.json for diagnostics.")
    return 0


def cmd_solve(args: argparse.Namespace) -> int:
    return cmd_bench(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="topopt")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--config", required=True)
    validate.set_defaults(func=cmd_validate)

    solve = sub.add_parser("solve")
    solve.add_argument("--benchmark", required=True)
    solve.add_argument("--config", required=True)
    solve.set_defaults(func=cmd_solve)

    bench = sub.add_parser("bench")
    bench.add_argument("--benchmark", required=True)
    bench.add_argument("--config", required=True)
    bench.set_defaults(func=cmd_bench)

    viz = sub.add_parser("viz")
    viz.add_argument("--run-id", required=True)
    viz.set_defaults(func=cmd_viz)

    traceability = sub.add_parser("traceability")
    traceability.set_defaults(func=cmd_traceability)

    certify = sub.add_parser("certify")
    certify.add_argument("--run-id", required=True)
    certify.set_defaults(func=cmd_certify)

    diagnose = sub.add_parser("diagnose")
    diagnose.set_defaults(func=cmd_diagnose)

    list_runs = sub.add_parser("list-runs")
    list_runs.set_defaults(func=cmd_list_runs)

    compare = sub.add_parser("compare")
    compare.add_argument("--left", required=True)
    compare.add_argument("--right", required=True)
    compare.set_defaults(func=cmd_compare)

    diff_config = sub.add_parser("diff-config")
    diff_config.add_argument("--left", required=True)
    diff_config.add_argument("--right", required=True)
    diff_config.set_defaults(func=cmd_diff_config)

    repo_check = sub.add_parser("repo-check")
    repo_check.set_defaults(func=cmd_repo_check)

    ci_verify = sub.add_parser("ci-verify")
    ci_verify.set_defaults(func=cmd_ci_verify)

    build_verify = sub.add_parser("build-verify")
    build_verify.set_defaults(func=cmd_build_verify)

    lint = sub.add_parser("lint")
    lint.add_argument("--fix", action="store_true")
    lint.set_defaults(func=cmd_lint)

    uq = sub.add_parser("uq")
    uq_sub = uq.add_subparsers(dest="uq_command", required=True)
    sample = uq_sub.add_parser("sample")
    sample.add_argument("--method", required=True, choices=["lhs"])
    sample.add_argument("--n", type=int, required=True)
    sample.add_argument("--seed", type=int, default=42)
    sample.add_argument("--attempts", type=int, default=20)
    sample.add_argument("--corr-weight", type=float, default=0.1)
    sample.add_argument("--no-maximin", action="store_true")
    sample.add_argument("--out", required=True)
    sample.set_defaults(func=cmd_uq_sample)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
