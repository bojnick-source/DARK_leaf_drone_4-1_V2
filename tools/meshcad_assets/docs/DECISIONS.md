# MeshCAD Assets NG — Engineering Decisions

This document records key engineering decisions, their rationale, and
alternatives that were considered but rejected.

## Decision Format

Each decision follows this template:

- **Decision ID**: Unique identifier
- **Date**: When the decision was made
- **Context**: Why the decision was needed
- **Decision**: What was decided
- **Rationale**: Why this option was chosen
- **Alternatives Rejected**: Other options considered
- **Consequences**: Impact of the decision

---

## Decisions

### DEC-001: Documentation-only initial scaffold

- **Date**: 2026-02-11
- **Context**: The MeshCAD Assets NG spec placeholder in the issue was not
  populated with the actual specification content. The prompt explicitly
  requires `TRACEABILITY.md` and `DECISIONS.md` under
  `tools/meshcad_assets/docs/`.
- **Decision**: Create the mandatory documentation artifacts
  (`TRACEABILITY.md` and `DECISIONS.md`) as the initial scaffold, without
  adding code that would implement an unprovided specification.
- **Rationale**: The core principles state "No silent guessing — if data is
  missing, do NOT invent defaults." Since the actual MeshCAD spec was not
  pasted, implementing code for an unknown spec would violate this principle.
  The documentation artifacts are explicitly required regardless of the spec
  content.
- **Alternatives Rejected**:
  - *Invent a plausible MeshCAD specification*: Rejected because it violates
    the "no silent guessing" principle and could produce incorrect
    functionality.
  - *Do nothing*: Rejected because the mandatory artifacts
    (`TRACEABILITY.md`, `DECISIONS.md`) are explicitly required by the prompt.
- **Consequences**: The repository gains the traceability and decision-logging
  infrastructure. When the full specification is provided, the scaffold can be
  extended with implementation-specific entries.

### DEC-002: Place artifacts under tools/meshcad_assets/docs/

- **Date**: 2026-02-11
- **Context**: The prompt specifies the exact paths
  `tools/meshcad_assets/docs/TRACEABILITY.md` and
  `tools/meshcad_assets/docs/DECISIONS.md`.
- **Decision**: Follow the specified paths exactly.
- **Rationale**: The prompt states "IMPLEMENT THEM" for requirements and
  specifies exact file paths. Following them exactly ensures traceability and
  avoids ambiguity.
- **Alternatives Rejected**:
  - *Place under docs/*: Rejected because the prompt specifies a different
    path.
  - *Place under src/*: Rejected because these are documentation artifacts,
    not source code.
- **Consequences**: A new `tools/meshcad_assets/` subtree is created. This
  follows the existing pattern where `tools/` contains validation and utility
  scripts.

### DEC-003: Preserve existing CI pipeline unchanged

- **Date**: 2026-02-11
- **Context**: The existing CI pipeline runs ruff lint, mypy type check,
  pytest, and mathlib validation. Adding documentation-only files should not
  affect any of these checks.
- **Decision**: Make no changes to the CI workflow or any existing source
  files. Only add new documentation files under `tools/meshcad_assets/docs/`.
- **Rationale**: The core principle "Minimal, reviewable diffs" and "fail-fast
  behavior" mandate keeping CI green at every step. Documentation-only
  additions are the safest change category.
- **Alternatives Rejected**:
  - *Add MeshCAD-specific CI steps*: Rejected because there is no MeshCAD
    code to validate yet.
- **Consequences**: CI remains green. No risk of regression.
