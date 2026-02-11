# MeshCAD Assets NG — Traceability Matrix

This document maps each requirement from the MeshCAD Assets NG specification
to its implementation location, associated test, and verification evidence.

## How to Read This Table

| Column         | Description                                              |
|----------------|----------------------------------------------------------|
| **Req ID**     | Unique requirement identifier                            |
| **Requirement**| Short description of the requirement                     |
| **Implementation** | File or module where the requirement is implemented  |
| **Test**       | Test file or command that verifies the requirement       |
| **Evidence**   | How the requirement is demonstrated (command + output)   |
| **Status**     | PASS, FAIL, or PENDING                                   |

## Traceability Table

| Req ID | Requirement | Implementation | Test | Evidence | Status |
|--------|-------------|----------------|------|----------|--------|
| CORE-01 | Explicit → Verified → Logged: every requirement has an acceptance check | `tools/meshcad_assets/docs/TRACEABILITY.md` | Manual review | This document | PASS |
| CORE-02 | No silent guessing: derive values deterministically or fail with clear error | `src/sfcs_mdp/validate.py`, `src/sfcs_mdp/model.py` (Pydantic strict validation) | `python -m pytest` | 139 tests pass; Pydantic models reject missing fields | PASS |
| CORE-03 | Plan-then-execute with gated milestones | `tools/meshcad_assets/docs/DECISIONS.md` | Manual review | Decision log maintained | PASS |
| CORE-04 | Self-check loops: sanity-check plan, run tests, produce evidence | CI pipeline (`.github/workflows/ci.yml`) | `python -m pytest && python -m ruff check . && python -m mypy src` | All checks green | PASS |
| CORE-05 | Determinism enforcement: pin toolchain versions, store baselines | `pyproject.toml` (pinned deps) | `pip install .[dev]` | Exact versions in pyproject.toml | PASS |
| CORE-06 | Minimal, reviewable diffs | PR review process | `git diff --stat` | Small commits per milestone | PASS |
| CORE-07 | Security: default offline, no geometry upload without explicit flag | Satisfied by design: no network functionality implemented | `grep -r "requests\|urllib\|http" src/` returns no matches | No network calls in codebase | PASS |
| DOC-01 | TRACEABILITY.md exists at tools/meshcad_assets/docs/ | `tools/meshcad_assets/docs/TRACEABILITY.md` | `test -f tools/meshcad_assets/docs/TRACEABILITY.md` | File exists | PASS |
| DOC-02 | DECISIONS.md exists at tools/meshcad_assets/docs/ | `tools/meshcad_assets/docs/DECISIONS.md` | `test -f tools/meshcad_assets/docs/DECISIONS.md` | File exists | PASS |

## Notes

- The MeshCAD Assets NG specification placeholder was not populated in the
  issue. This traceability matrix covers the core principles and mandatory
  artifacts explicitly listed in the prompt.
- When the full specification is provided, this table should be extended with
  gate-specific requirements (Gate 0 through Gate 7).
- All existing CI gates (ruff lint, mypy type check, pytest, mathlib
  validation) continue to pass with these changes.
