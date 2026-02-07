# Traceability

| ID | Requirement summary | Implementation / Evidence |
| --- | --- | --- |
| REQ-NOQ-001 | No questions | docs/upgrade_plan.md | 
| REQ-NOQ-002 | Treat repo as pre-existing | docs/upgrade_plan.md |
| REQ-NOQ-003 | Auto-discover repo + plan | docs/upgrade_plan.md |
| REQ-NOQ-004 | End-to-end verified CI-small run | scripts/certificate_check.py, src/topopt/cli.py |
| REQ-TRACE-001 | Store prompt verbatim | docs/spec_prompt.txt |
| REQ-TRACE-002 | MUST/SHALL ID policy | scripts/prompt_must_id_check.py |
| REQ-TRACE-003 | Prompt must ID check script | scripts/prompt_must_id_check.py |
| REQ-TRACE-004 | Prompt IDs in requirements | scripts/traceability_check.py |
| REQ-TRACE-005 | Requirements mapped | scripts/traceability_check.py, docs/traceability.md |
| REQ-TRACE-006 | Traceability check + json | scripts/traceability_check.py |
| REQ-TRACE-010 | Requirements + traceability docs | docs/requirements.md, docs/traceability.md |
| SEC-LIC-001 | No proprietary copying | docs/migration_guide.md |
| SEC-LIC-002 | No invented APIs | docs/migration_guide.md |
| REQ-LEAP-001 | Use “Noyron” spelling | docs/migration_guide.md |
| REQ-LEAP-002 | Integrations as adapters | src/topopt/core/solver.py |
| REQ-LEAP-003 | Open fallback geometry backend | src/topopt/core/solver.py |
| REQ-MIS-001 | Claims testable | tests/topopt/test_lhs.py |
| REQ-MIS-002 | Stop on failure with repro | src/topopt/cli.py |
| REQ-MIS-003 | DONE only after verified cert | scripts/certificate_check.py |
| REQ-MIS-004 | Explicit simplifications | docs/migration_guide.md |
| REQ-DEF-001 | Default parameter contract | configs/default_parameters.json |
| REQ-DEF-002 | Defaults include units/bounds | configs/default_parameters.json |
| REQ-DEF-003 | Deterministic CI defaults | configs/default_parameters.json |
| REQ-DEF-004 | Missing items listed | docs/open_questions.md |
| REQ-TGT-001 | Monorepo layout | docs/upgrade_plan.md |
| REQ-TGT-002 | Data contract schemas | schemas/config.schema.json, schemas/results.schema.json, schemas/artifact.schema.json, schemas/certificate.schema.json |
| REQ-TGT-003 | CLI commands | src/topopt/cli.py |
| REQ-REPO-001 | topopt repo-check | src/topopt/cli.py |
| REQ-CI-001 | topopt ci-verify | src/topopt/cli.py, ci/ci_small.sh |
| REQ-BUILD-001 | build_on/off modes | ci/build_on.sh, ci/build_off.sh, src/topopt/cli.py |
| PO-BUILD-001 | build_off optional deps fail | ci/build_off.sh |
| REQ-LINT-001 | Enforce lint/types | .github/workflows/ci.yaml |
| REQ-LINT-002 | topopt lint | src/topopt/cli.py |
| REQ-ROB-001 | Primary + secondary methods | src/topopt/core/robust.py |
| REQ-UQ-LHS-001 | LHS implemented | src/topopt/uq/lhs.py |
| REQ-UQ-LHS-002 | LHS features | src/topopt/uq/lhs.py |
| REQ-UQ-LHS-003 | Batching strategy | src/topopt/uq/lhs.py |
| REQ-UQ-LHS-004 | SLHS test if used | tests/topopt/test_lhs.py |
| REQ-UQ-LHS-005 | Fixed batching test | tests/topopt/test_lhs.py |
| REQ-UQ-LHS-006 | LHS metrics | src/topopt/uq/metrics.py |
| REQ-UQ-LHS-007 | CLI sample output | src/topopt/cli.py |
| REQ-UQ-LHS-008 | LHS tests | tests/topopt/test_lhs.py |
| REQ-UQ-LHS-009 | CI runs LHS tests | .github/workflows/ci.yaml |
| REQ-UQ-LHS-010 | Certificate fields | schemas/certificate.schema.json, src/topopt/core/robust.py |
| PO-UQ-LHS-001 | Thresholds -> NOT_VERIFIED | src/topopt/core/robust.py |
| REQ-UQ-INT-001 | LHS integrated + cross-check | src/topopt/core/robust.py |
| REQ-UQ-INT-002 | Variance reduction | src/topopt/core/robust.py |
| REQ-UQ-INT-003 | Parallel sample eval | src/topopt/core/robust.py |
| REQ-VIZ-001 | UQ section in viz | src/topopt/viz.py, docs/viz/index.html |
| BENCH-001 | MBB beam benchmark | benchmarks/mbb.json |
| BENCH-002 | Cantilever benchmark | benchmarks/cantilever.json |
| BENCH-003 | L-bracket benchmark | benchmarks/l_bracket.json |
| REQ-CERT-001 | Certificate includes UQ/LHS | schemas/certificate.schema.json |
| REQ-ENV-001 | Dockerfile + locks | Dockerfile, package-lock.json, poetry.lock |
| REQ-EXEC-001 | Upgrade plan + migration guide | docs/upgrade_plan.md, docs/migration_guide.md |
| REQ-EXEC-002 | Early wiring | docs/upgrade_plan.md |
| REQ-EXEC-003 | LHS/UQ integration | docs/upgrade_plan.md |
| REQ-EXEC-004 | CI-small verified run | ci/ci_small.sh |
| REQ-OFF-001 | No-network CI pass | .github/workflows/ci.yaml, docs/offline_ci.md |
| REQ-OFF-002 | pytest passes without NumPy | tests/topopt/test_lhs.py |
| REQ-OFF-003 | Optional NumPy acceleration | src/topopt/uq/metrics.py |
| REQ-OFF-010 | No questions | docs/upgrade_plan.md |
| REQ-OFF-011 | Inventory imports | docs/upgrade_plan.md |
| REQ-OFF-012 | Fixes in-place | docs/offline_ci.md |
| REQ-OFF-BLD-001 | build_off/build_on lanes | .github/workflows/ci.yaml |
| REQ-OFF-BLD-002 | build_off NumPy tripwire | tests/topopt/test_lhs.py |
| REQ-OFF-BLD-003 | build_on optional | .github/workflows/ci.yaml |
| REQ-OFF-DEP-001 | No internet pip | .github/workflows/ci.yaml |
| REQ-OFF-DEP-002 | Offline strategy | docs/offline_ci.md |
| REQ-OFF-DEP-003 | build_off without NumPy | src/topopt/uq/lhs.py |
| REQ-OFF-UQ-001 | NumPy-free LHS | src/topopt/uq/lhs.py |
| REQ-OFF-UQ-002 | Pure-Python LHS | src/topopt/uq/lhs.py |
| REQ-OFF-UQ-003 | Pure-Python metrics | src/topopt/uq/metrics.py |
| REQ-OFF-UQ-004 | Optional NumPy acceleration | src/topopt/uq/metrics.py |
| PO-OFF-UQ-001 | Cross-backend agreement test | tests/topopt/test_lhs.py |
| REQ-OFF-TST-001 | LHS tests without NumPy | tests/topopt/test_lhs.py |
| REQ-OFF-TST-002 | NumPy import tripwire | tests/topopt/test_lhs.py |
| REQ-OFF-TST-003 | pytest -q build_off | .github/workflows/ci.yaml |
| REQ-OFF-CI-001 | CI lanes | .github/workflows/ci.yaml |
| REQ-OFF-CI-002 | No-index installs | .github/workflows/ci.yaml |
| REQ-OFF-CI-003 | CI summary | scripts/ci_report.py, .github/workflows/ci.yaml |
| REQ-OFF-ART-001 | build_report/test_report/import_audit/perf_report | scripts/ci_report.py, pytest/__main__.py, scripts/perf_tripwire.py |
| REQ-OFF-ART-002 | failure repro command | scripts/ci_report.py |
| REQ-OFF-DELIV-001 | NumPy-free code | src/topopt/uq/lhs.py, src/topopt/uq/metrics.py |
| REQ-OFF-DELIV-002 | Updated tests | tests/topopt/test_lhs.py |
| REQ-OFF-DELIV-003 | Updated CI | .github/workflows/ci.yaml |
| REQ-OFF-DELIV-004 | Offline CI docs | docs/offline_ci.md |
| REQ-OFF-STOP-001 | Replace external downloads | docs/offline_ci.md |
| REQ-A3-001 | No questions | docs/upgrade_plan.md |
| REQ-A3-002 | Inventory + apply changes | docs/upgrade_plan.md |
| REQ-A3-003 | Backward compatibility | docs/migration_guide.md |
| REQ-A3-010 | Offline build_off | .github/workflows/ci.yaml |
| REQ-A3-011 | Fail fast on network fetch | .github/workflows/ci.yaml, scripts/no_network_sentinel.py |
| REQ-A3-012 | Required artifacts | scripts/ci_artifact_check.py, .github/workflows/ci.yaml |
| REQ-A3-013 | No silent skips | pytest/__main__.py |
| REQ-A3-CI-001 | Offline env vars | .github/workflows/ci.yaml |
| REQ-A3-CI-002 | No network pip | .github/workflows/ci.yaml |
| REQ-A3-CI-003 | No-network sentinel | scripts/no_network_sentinel.py |
| REQ-A3-CI-004 | build_on optional | .github/workflows/ci.yaml |
| REQ-A3-IMP-001 | Forbidden imports list | pytest/__main__.py |
| REQ-A3-IMP-002 | Forbidden import tripwire | tests/topopt/test_lhs.py |
| REQ-A3-IMP-003 | Import audit | pytest/__main__.py |
| REQ-A3-IMP-004 | import_audit.json fields | pytest/__main__.py, schemas/ci/import_audit.schema.json |
| REQ-A3-PERF-001 | Runtime budgets | pytest/__main__.py, scripts/perf_tripwire.py |
| REQ-A3-PERF-002 | Fail on perf regressions | scripts/perf_tripwire.py |
| REQ-A3-PERF-003 | perf_report.json | scripts/perf_tripwire.py, schemas/ci/perf_report.schema.json |
| REQ-A3-ART-001 | Required artifacts | scripts/ci_artifact_check.py, schemas/ci/*.schema.json |
| REQ-A3-ART-002 | Artifact checker | scripts/ci_artifact_check.py |
| REQ-A3-ART-003 | CI artifact gate | .github/workflows/ci.yaml |
| REQ-A3-SKIP-001 | Skip report | pytest/__main__.py, schemas/ci/skip_report.schema.json |
| REQ-A3-SKIP-002 | Skip reason enforcement | pytest/__main__.py |
| REQ-A3-SKIP-003 | Skip cap | pytest/__main__.py |
| REQ-A3-REPO-001 | repo-check validation | src/topopt/cli.py |
| REQ-A3-REPO-002 | CI repo-check | .github/workflows/ci.yaml |
| REQ-A3-REPO-003 | repo_check.json | src/topopt/cli.py, schemas/ci/repo_check.schema.json |
| REQ-A3-DOC-001 | offline_ci_hardening.md | docs/offline_ci_hardening.md |
| REQ-A3-DOC-002 | Repro commands | scripts/ci_report.py, scripts/perf_tripwire.py |
| REQ-A3-DONE-001 | DONE criteria | docs/requirements.md |
| REQ-A3P-001 | No questions | docs/upgrade_plan.md |
| REQ-A3P-002 | Inventory + apply changes | docs/upgrade_plan.md |
| REQ-A3P-003 | Backward compatibility | docs/migration_guide.md |
| REQ-A3P-010 | Offline build_off | .github/workflows/ci.yaml |
| REQ-A3P-011 | Fail on network fetching | .github/workflows/ci.yaml, scripts/no_network_sentinel.py |
| REQ-A3P-012 | Required artifacts | scripts/ci_artifact_check.py, .github/workflows/ci.yaml |
| REQ-A3P-013 | No silent skips | pytest/__main__.py |
| REQ-A3P-CI-001 | Offline env vars | .github/workflows/ci.yaml |
| REQ-A3P-CI-002 | No network pip | .github/workflows/ci.yaml |
| REQ-A3P-CI-003 | No-network sentinel | scripts/no_network_sentinel.py |
| REQ-A3P-CI-004 | build_on optional | .github/workflows/ci.yaml |
| REQ-A3P-ART-001 | Required ci_out artifacts | scripts/ci_artifact_check.py |
| REQ-A3P-ART-002 | Artifact schemas in schemas/ci | schemas/ci/*.schema.json |
| REQ-A3P-ART-003 | ci_artifact_check validator | scripts/ci_artifact_check.py |
| REQ-A3P-ART-004 | Always-run artifact check | .github/workflows/ci.yaml |
| REQ-A3P-ART-005 | Upload ci_out | .github/workflows/ci.yaml |
| REQ-A3P-SKIP-001 | Skip reason enforcement | pytest/__main__.py |
| REQ-A3P-SKIP-002 | Skip capture hook | pytest/__main__.py |
| REQ-A3P-SKIP-003 | SKIP_CAP=0 in build_off | pytest/__main__.py |
| REQ-A3P-SKIP-004 | build_on skips recorded | pytest/__main__.py |
| REQ-A3P-IMP-001 | Forbidden imports | pytest/__main__.py |
| REQ-A3P-IMP-002 | Fail on forbidden imports | pytest/__main__.py |
| REQ-A3P-IMP-003 | import_audit.json fields | pytest/__main__.py, schemas/ci/import_audit.schema.json |
| REQ-A3P-PERF-001 | Runtime budgets | pytest/__main__.py, scripts/perf_tripwire.py |
| REQ-A3P-PERF-002 | Fail on perf regressions | scripts/perf_tripwire.py |
| REQ-A3P-REPO-001 | repo_check.json | src/topopt/cli.py, schemas/ci/repo_check.schema.json |
| REQ-A3P-REPO-002 | CI repo-check | .github/workflows/ci.yaml |
| REQ-A3P-DOC-001 | ci_artifacts.md | docs/ci_artifacts.md |
| REQ-A3P-DOC-002 | Repro commands | scripts/ci_report.py, scripts/perf_tripwire.py |
| REQ-A3P-DONE-001 | DONE criteria | docs/requirements.md |
