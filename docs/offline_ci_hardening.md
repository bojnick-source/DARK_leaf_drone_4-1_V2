# Offline CI hardening

## build_off vs build_on
- build_off: stdlib-only, no external downloads, forbidden-import tripwires active.
- build_on: optional acceleration if deps exist locally; not required for offline CI success.

## Forbidden imports policy
build_off forbids: numpy, scipy, pandas, matplotlib, petsc4py, jax, cupy. Any import attempt fails.

## Performance budgets
- Tests: `python -m pytest -q tests/topopt` enforced by `TOPOPT_TEST_BUDGET_S`.
- LHS: `topopt uq sample --method lhs --n 256` equivalent enforced by `scripts/perf_tripwire.py`.

## Required CI artifacts
Every run must emit:
- ci_out/build_report.json
- ci_out/test_report.json
- ci_out/import_audit.json
- ci_out/perf_report.json
- ci_out/skip_report.json
- ci_out/repo_check.json

Schemas live in `/schemas/ci` and are enforced by `scripts/ci_artifact_check.py`.

## Skip policy
All skips must include a reason with missing dependency, how to enable it, and VERIFIED impact.
Skip cap defaults to 0 in build_off.

## Offline enforcement
build_off runs a no-network sentinel and blocks any pip network access via environment flags.

## Repro commands
CI failures should print minimal repro commands and point to the relevant ci_out JSON files.
