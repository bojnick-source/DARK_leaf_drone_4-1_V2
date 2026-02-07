# Upgrade plan

## Inventory summary
- Repository contains mixed C++/Python/Node assets with existing CI and CMake builds.
- New monorepo folders added: /benchmarks /docs /scripts /ci /runs /configs /schemas.

## Execution plan aligned to requirements
1. Capture the spec prompt and requirements artifacts (REQ-TRACE-001, REQ-TRACE-010).
2. Add traceability and ID policy tooling (REQ-TRACE-002, REQ-TRACE-003, REQ-TRACE-004, REQ-TRACE-005, REQ-TRACE-006).
3. Add data contracts, defaults, and open questions (REQ-DEF-001, REQ-DEF-002, REQ-DEF-003, REQ-DEF-004, REQ-TGT-002).
4. Implement CLI commands, repo-check, ci-verify, build-verify, and lint gates (REQ-TGT-003, REQ-REPO-001, REQ-CI-001, REQ-BUILD-001, REQ-LINT-001, REQ-LINT-002).
5. Implement LHS + UQ integration, metrics, and tests (REQ-UQ-LHS-001..REQ-UQ-LHS-010, REQ-UQ-INT-001..REQ-UQ-INT-003).
6. Add benchmarks, viz, certificate outputs, and CI-small run script (BENCH-001..BENCH-003, REQ-VIZ-001, REQ-CERT-001, REQ-EXEC-004).
7. Add container build to satisfy REQ-ENV-001 and CI steps to execute new checks.

## Status
- Completed artifacts and scripts are tracked via docs/traceability.md.
