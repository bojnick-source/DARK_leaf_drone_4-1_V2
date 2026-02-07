# CI artifacts

## Required artifacts
Every CI lane must emit these files under `ci_out/`:
- build_report.json
- test_report.json
- import_audit.json
- perf_report.json
- skip_report.json
- repo_check.json

## Schemas
Schemas live under `schemas/ci/` and are enforced by `scripts/ci_artifact_check.py`.

## Artifact checker
`scripts/ci_artifact_check.py` verifies:
- each required artifact exists
- JSON matches its schema
- reports missing/invalid files with explicit paths

## Skip report
`ci_out/skip_report.json` lists skipped tests and reasons. Fix skips by installing missing optional deps or adjusting build_on configuration.

## Repro commands
CI failures must print a minimal repro command and the relevant `ci_out/*.json` paths to inspect.
