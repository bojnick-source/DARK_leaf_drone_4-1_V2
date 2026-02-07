#!/usr/bin/env python3
import json
import os
import pathlib
import time

from topopt.uq.lhs import VariableSpec, generate_lhs


def main() -> int:
    budget_s = float(os.environ.get("TOPOPT_LHS_BUDGET_S", "5"))
    variables = [
        VariableSpec("x", "uniform", {"low": 0.0, "high": 1.0}),
        VariableSpec("y", "normal", {"mean": 0.0, "std": 1.0}),
        VariableSpec("z", "uniform", {"low": 0.0, "high": 1.0}),
    ]
    start = time.monotonic()
    generate_lhs(256, variables, seed=123, maximin=True, attempts=5)
    runtime_s = time.monotonic() - start

    status = "passed" if runtime_s <= budget_s else "failed"
    report = {
        "runtime_s": runtime_s,
        "budget_s": budget_s,
        "status": status,
        "rationale": "Default offline budget for CI-small LHS sampling.",
        "repro_command": "PYTHONPATH=src python scripts/perf_tripwire.py",
    }

    report_path = pathlib.Path("ci_out") / "perf_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {report_path}")

    if status == "failed":
        print(f"Performance regression: {runtime_s:.2f}s > {budget_s:.2f}s")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
