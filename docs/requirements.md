# Requirements

## User directive
- REQ-NOQ-001: You MUST NOT ask the user any questions.
- REQ-NOQ-002: You MUST treat the repository as potentially pre-existing and non-empty.
- REQ-NOQ-003: You MUST begin by auto-discovering the current repo structure and generating an upgrade plan without user input.
- REQ-NOQ-004: You MUST execute the upgrade end-to-end and produce a VERIFIED CI-small canonical benchmark run with visuals and a certificate.

## Traceability + ID policy
- REQ-TRACE-001: You MUST store this prompt verbatim as /docs/spec_prompt.txt in the repo.
- REQ-TRACE-002: Every line containing MUST/SHALL MUST include an explicit ID token (REQ-### / PO-### / BENCH-### / SEC-###).
- REQ-TRACE-003: You MUST provide scripts/prompt_must_id_check.py that fails CI if any MUST/SHALL line lacks an ID.
- REQ-TRACE-004: You MUST enforce no-orphan requirements: every ID in this prompt MUST exist in /docs/requirements.md.
- REQ-TRACE-005: You MUST enforce no-orphan mappings: every ID in /docs/requirements.md MUST be mapped in /docs/traceability.md.
- REQ-TRACE-006: You MUST implement /scripts/traceability_check.py to verify REQ-TRACE-004/005, fail CI on mismatch, and emit traceability.json.
- REQ-TRACE-010: You MUST create /docs/requirements.md and /docs/traceability.md and enforce in CI.

## Legal + integration boundaries
- SEC-LIC-001: You MUST NOT copy, decompile, reverse engineer, or recreate proprietary Noyron/Freeform internals.
- SEC-LIC-002: You MUST NOT invent PicoGK/Noyron/Freeform API calls.
- REQ-LEAP-001: You MUST use spelling “Noyron” in docs.
- REQ-LEAP-002: You MUST implement PicoGK/Noyron/Freeform integrations ONLY as plugin adapters + placeholders unless official SDK/API exists inside the repo.
- REQ-LEAP-003: You MUST provide a functional open fallback geometry backend (SDF + marching cubes) so the full pipeline runs end-to-end without PicoGK.

## Mission rules
- REQ-MIS-001: Every claim MUST be testable via code + tests + artifacts + traceability.
- REQ-MIS-002: Any instability or verification failure MUST STOP, dump state, output minimal repro + ranked debug checklist.
- REQ-MIS-003: DONE MAY ONLY be printed when results_certificate.json overall_status == VERIFIED for at least one CI-small canonical benchmark AND certificate_check passes.
- REQ-MIS-004: You MUST NOT “pass” by silently weakening physics; any simplification MUST be explicit and recorded.

## Defaults policy
- REQ-DEF-001: You MUST generate or adopt a complete default Parameter Contract.
- REQ-DEF-002: Every default numeric value MUST include units, bounds, rationale/source, and an uncertainty model.
- REQ-DEF-003: Defaults MUST make canonical benchmarks run deterministically and complete in CI.
- REQ-DEF-004: Unknown parameters MUST be auto-filled as USER-AUTHORIZED DEFAULTS; missing items MUST be listed in /docs/open_questions.md.

## Target end-state
- REQ-TGT-001: A clean monorepo layout with stable interfaces: /src /tests /benchmarks /docs /scripts /ci /runs /configs /schemas.
- REQ-TGT-002: A consistent data contract: config schema + results schema + artifact manifest schema + certificate schema.
- REQ-TGT-003: A robust CLI that supports: validate, solve, viz, bench, traceability, certify, diagnose, list-runs, compare, diff-config, repo-check, ci-verify, build-verify, lint, and uq.

## Repository + CI + build
- REQ-REPO-001: You MUST implement `topopt repo-check`.
- REQ-CI-001: You MUST implement `topopt ci-verify`; CI MUST run it.
- REQ-BUILD-001: You MUST implement build_on and build_off modes; CI MUST run both.
- PO-BUILD-001: build_off importing heavy optional deps MUST fail CI.

## Lint + format + types
- REQ-LINT-001: You MUST enforce formatting/lint/types in CI.
- REQ-LINT-002: You MUST provide `topopt lint` and `topopt lint --fix`.

## Robustness + UQ + LHS
- REQ-ROB-001: You MUST implement one primary robust method and one distinct secondary verification method.
- REQ-UQ-LHS-001: You MUST implement Latin Hypercube Sampling (LHS) as a first-class sampler for uncertainty quantification and robust optimization.
- REQ-UQ-LHS-002: LHS MUST support: (a) maximin criterion (space-filling), (b) correlation control, (c) seeded determinism, (d) marginals (uniform/normal/lognormal/triangular), (e) mixed continuous + discrete variables via stratified mapping.
- REQ-UQ-LHS-003: LHS MUST implement one of the following incremental/batched strategies with explicit behavior: (A) Sliced LHS (SLHS) OR (B) fixed-schedule batching with explicit non-SLHS labeling.
- REQ-UQ-LHS-004: If the repo implements SLHS, it MUST provide a test asserting slice-level stratification and union-level stratification per dimension.
- REQ-UQ-LHS-005: If the repo implements FIXED-SCHEDULE batching only, it MUST provide a test asserting union-level stratification and deterministic batch partitioning; it MUST NOT claim slice-level stratification.
- REQ-UQ-LHS-006: You MUST implement at least two LHS quality metrics and log them: centered L2-discrepancy, minimum pairwise distance, pairwise correlation bounds (any two).
- REQ-UQ-LHS-007: You MUST implement `topopt uq sample --method lhs --n N --out samples.parquet` and integrate samples into robust runs.
- REQ-UQ-LHS-008: You MUST provide tests that verify union-level stratification, reproducibility, marginal distribution checks, and quality metric improvement across maximin attempts.
- REQ-UQ-LHS-009: CI MUST run a small LHS sampler test suite and record sampler quality metrics in artifacts.
- REQ-UQ-LHS-010: results_certificate.json MUST include: lhs_enabled, n_samples, seed, batching_mode ∈ {SLHS, BATCHED-NON-SLHS}, lhs_quality_metrics, and uq_mode_verdict.
- PO-UQ-LHS-001: If configured LHS quality thresholds are violated, robust mode MUST be NOT_VERIFIED and remediation MUST be recorded.

## Advanced UQ integration
- REQ-UQ-INT-001: You MUST integrate LHS into robust objectives and cross-check against a different estimator as the secondary method.
- REQ-UQ-INT-002: You MUST implement and log at least one variance reduction technique for the secondary estimator when feasible; if infeasible, you MUST record “N/A” with reason.
- REQ-UQ-INT-003: You MUST support parallel evaluation of samples and record per-sample solver stats and failures.

## Results + exports + viz
- REQ-VIZ-001: viz/index.html MUST include a UQ section showing LHS configuration, batching_mode, quality metrics, sample projection plots, and robust objective history.

## Benchmarks
- BENCH-001: MBB beam.
- BENCH-002: Cantilever with tip load.
- BENCH-003: L-bracket / compliant-mechanism-style case.

## Certificate + environment
- REQ-CERT-001: results_certificate.json MUST include UQ/LHS status and metrics.
- REQ-ENV-001: Dockerfile + pinned lockfiles; CI MUST run in container.

## Upgrade execution order
- REQ-EXEC-001: Inventory repo and write /docs/upgrade_plan.md and /docs/migration_guide.md.
- REQ-EXEC-002: Wire traceability + certificate + repo-check + ci-verify + build-verify + lint early.
- REQ-EXEC-003: Implement LHS + UQ integration + tests + logging + viz before declaring robust VERIFIED.
- REQ-EXEC-004: Produce CI-small VERIFIED run; print DONE only if certificate_check passes.

## Offline CI hardening
- REQ-OFF-001: You MUST make CI pass in a no-network environment by removing any hard dependency on PyPI downloads during CI runs.
- REQ-OFF-002: You MUST ensure `python -m pytest tests/topopt` passes in build_off WITHOUT NumPy installed.
- REQ-OFF-003: You MUST keep an optional accelerated path (NumPy/SciPy) for build_on, but build_off MUST remain fully functional without them.
- REQ-OFF-010: You MUST NOT ask the user any questions.
- REQ-OFF-011: You MUST begin by inventorying imports and dependency points in the repo to identify where NumPy is required.
- REQ-OFF-012: You MUST implement fixes in-place and update tests and CI accordingly.
- REQ-OFF-BLD-001: You MUST define build_off and build_on install/test lanes.
- REQ-OFF-BLD-002: build_off MUST fail CI if it imports NumPy/SciPy.
- REQ-OFF-BLD-003: build_on MUST run if deps available, but MUST NOT be required for CI pass in no-network mode.
- REQ-OFF-DEP-001: CI MUST NOT run `pip install .[dev]` if it pulls from the internet.
- REQ-OFF-DEP-002: You MUST implement one offline dependency strategy.
- REQ-OFF-DEP-003: build_off MUST be runnable end-to-end without NumPy.
- REQ-OFF-UQ-001: You MUST refactor UQ LHS code so build_off does not import or require NumPy.
- REQ-OFF-UQ-002: You MUST implement a pure-Python LHS sampler with deterministic RNG, stratification, maximin, and correlation control.
- REQ-OFF-UQ-003: You MUST implement pure-Python UQ metrics for build_off.
- REQ-OFF-UQ-004: You MUST keep optional NumPy acceleration with fallback when not installed.
- PO-OFF-UQ-001: You MUST add cross-backend agreement tests when NumPy is available, otherwise SKIP with reason.
- REQ-OFF-TST-001: You MUST update tests to validate LHS behavior without NumPy.
- REQ-OFF-TST-002: You MUST add a dependency smoke test that fails if NumPy is importable in build_off.
- REQ-OFF-TST-003: You MUST ensure `pytest -q` passes in build_off without network.
- REQ-OFF-CI-001: You MUST modify CI to run build_off and optional build_on lanes.
- REQ-OFF-CI-002: CI MUST never attempt to fetch packages from the internet.
- REQ-OFF-CI-003: CI MUST print a summary indicating mode, NumPy acceleration, and skipped tests.
- REQ-OFF-ART-001: You MUST write `ci_out/build_report.json` with mode, deps, and pass/fail signals.
- REQ-OFF-ART-002: Any failure MUST include a minimal repro command.
- REQ-OFF-DELIV-001: Updated source code for NumPy-free build_off plus optional acceleration.
- REQ-OFF-DELIV-002: Updated tests for LHS and dependency tripwires.
- REQ-OFF-DELIV-003: Updated CI workflow for no-network pass.
- REQ-OFF-DELIV-004: Documentation in /docs/offline_ci.md.
- REQ-OFF-STOP-001: If any step still requires external downloads, STOP and replace it with a repo-contained alternative.

## A+++ hardening
- REQ-A3-001: You MUST NOT ask the user any questions.
- REQ-A3-002: You MUST inventory the repo and CI workflows and apply changes in-place.
- REQ-A3-003: You MUST preserve backward compatibility or provide a migration script.
- REQ-A3-010: build_off MUST pass fully offline without NumPy.
- REQ-A3-011: CI MUST fail fast if any step attempts network package fetching in build_off.
- REQ-A3-012: CI MUST produce and upload required artifacts every run and fail if missing.
- REQ-A3-013: CI MUST fail if tests are skipped without explicit SKIPPED reasons.
- REQ-A3-CI-001: build_off MUST export offline pip env vars.
- REQ-A3-CI-002: build_off MUST NOT run pip that can fetch from network.
- REQ-A3-CI-003: build_off MUST run a no-network sentinel step.
- REQ-A3-CI-004: build_on MAY run with optional deps but is not required for offline success.
- REQ-A3-IMP-001: build_off MUST NOT import forbidden heavy deps.
- REQ-A3-IMP-002: pytest tripwire MUST fail if forbidden import is importable.
- REQ-A3-IMP-003: import audit MUST record imports and fail on forbidden.
- REQ-A3-IMP-004: ci_out/import_audit.json MUST include mode/forbidden/detected/pass-fail.
- REQ-A3-PERF-001: enforce runtime budgets for tests and LHS sampling.
- REQ-A3-PERF-002: CI MUST fail if runtime exceeds thresholds.
- REQ-A3-PERF-003: ci_out/perf_report.json MUST include timings/thresholds/pass-fail.
- REQ-A3-ART-001: CI MUST generate required artifacts every run.
- REQ-A3-ART-002: scripts/ci_artifact_check.py MUST validate required artifacts vs schemas.
- REQ-A3-ART-003: CI MUST run ci_artifact_check and fail on errors.
- REQ-A3-SKIP-001: skipped tests MUST write explicit reasons to skip_report.json.
- REQ-A3-SKIP-002: pytest hook MUST fail on vague skip reasons.
- REQ-A3-SKIP-003: skip count MUST not exceed cap.
- REQ-A3-REPO-001: repo-check MUST validate layout, schemas, and artifact tooling.
- REQ-A3-REPO-002: CI MUST run repo-check in build_off.
- REQ-A3-REPO-003: repo-check MUST emit ci_out/repo_check.json.
- REQ-A3-DOC-001: docs/offline_ci_hardening.md MUST describe policies.
- REQ-A3-DOC-002: CI failures MUST print repro command and ci_out paths.
- REQ-A3-DONE-001: DONE only when all A3 checks pass.

## A+++ power-up
- REQ-A3P-001: You MUST NOT ask the user any questions.
- REQ-A3P-002: You MUST inventory existing CI/workflows/tests and apply changes in-place.
- REQ-A3P-003: You MUST preserve backward compatibility or provide a migration path.
- REQ-A3P-010: build_off MUST pass fully offline without NumPy.
- REQ-A3P-011: CI MUST fail if any step attempts network fetching in build_off.
- REQ-A3P-012: CI MUST generate and upload required artifacts every run.
- REQ-A3P-013: CI MUST fail if tests are skipped without explicit reasons.
- REQ-A3P-CI-001: build_off MUST export offline pip env vars.
- REQ-A3P-CI-002: build_off MUST NOT run pip that can fetch from network.
- REQ-A3P-CI-003: build_off MUST run a no-network sentinel check.
- REQ-A3P-CI-004: build_on MAY exist but not required for offline success.
- REQ-A3P-ART-001: Every CI lane MUST generate required artifacts under ci_out/.
- REQ-A3P-ART-002: JSON Schemas for artifacts MUST live under /schemas/ci/.
- REQ-A3P-ART-003: scripts/ci_artifact_check.py MUST validate required artifacts.
- REQ-A3P-ART-004: CI MUST run ci_artifact_check in an always-run step.
- REQ-A3P-ART-005: CI MUST upload ci_out/ each run.
- REQ-A3P-SKIP-001: Any skipped test MUST include a specific reason.
- REQ-A3P-SKIP-002: pytest hook MUST capture skips and fail on vague reasons.
- REQ-A3P-SKIP-003: build_off MUST enforce SKIP_CAP=0 unless justified.
- REQ-A3P-SKIP-004: build_on skips MUST be recorded and not claim VERIFIED.
- REQ-A3P-IMP-001: build_off MUST forbid numpy/scipy/pandas/matplotlib/petsc4py/jax/cupy.
- REQ-A3P-IMP-002: build_off tests MUST fail on forbidden imports.
- REQ-A3P-IMP-003: import audit MUST write ci_out/import_audit.json with required fields.
- REQ-A3P-PERF-001: build_off MUST enforce runtime budgets and record perf_report.json.
- REQ-A3P-PERF-002: CI MUST fail if budgets are exceeded.
- REQ-A3P-REPO-001: repo-check MUST emit ci_out/repo_check.json with per-check status.
- REQ-A3P-REPO-002: CI MUST run repo-check in build_off lane.
- REQ-A3P-DOC-001: docs/ci_artifacts.md MUST describe artifacts and schemas.
- REQ-A3P-DOC-002: CI failures MUST print repro command and ci_out paths.
- REQ-A3P-DONE-001: DONE only when all A3P checks pass.
