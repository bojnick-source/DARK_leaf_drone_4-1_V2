# Offline CI guide

This repository supports two build lanes designed for restricted, no-network environments.

## build_off (offline-minimal)
- Uses stdlib-only Python paths.
- Does not require NumPy/SciPy.
- Runs `python -m pytest -q tests/topopt` with `TOPOPT_BUILD_MODE=OFF`.
  - A lightweight local pytest shim is provided for offline execution.
- Enforces runtime budgets via `TOPOPT_TEST_BUDGET_S` and `TOPOPT_LHS_BUDGET_S`.

Example:
```
TOPOPT_BUILD_MODE=OFF PYTHONPATH=src python -m pytest -q tests/topopt
```

## build_on (full)
- Optional acceleration when NumPy is available locally.
- Enables the NumPy-backed metric fast path automatically if installed.

Example (if NumPy is installed locally):
```
PYTHONPATH=src python -m pytest -q tests/topopt
```

## Optional dependency paths
- For offline environments, avoid `pip install` against external indexes.
- If a local wheelhouse is available, install with `PIP_NO_INDEX=1` and `--find-links`.

## Reporting
CI emits `ci_out/build_report.json` containing the mode, dependency visibility, and test commands used.
Additional artifacts:
- `ci_out/test_report.json` for pass/fail/skip counts and runtime.
- `ci_out/import_audit.json` for forbidden import auditing.
- `ci_out/perf_report.json` for LHS runtime tripwire results.
