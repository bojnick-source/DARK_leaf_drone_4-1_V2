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
- **Decision**: Make no changes to the CI workflow. New code is added in the
  standard `src/reidce/` location so existing mypy and ruff checks cover it
  automatically.
- **Rationale**: The core principle "Minimal, reviewable diffs" and "fail-fast
  behavior" mandate keeping CI green at every step.
- **Alternatives Rejected**:
  - *Add MeshCAD-specific CI steps*: Rejected because the existing pipeline
    already covers linting, type-checking, and testing for `src/` modules.
- **Consequences**: CI remains green. No risk of regression.

### DEC-004: Implement mesh validation as reidce.mesh_validator module

- **Date**: 2026-02-12
- **Context**: The original prompt was an experiment. User requested actual
  code. The `reidce` package already has `cad_rendering.py` with Vec3,
  Triangle, CadMesh, and mesh utility functions.
- **Decision**: Add `src/reidce/mesh_validator.py` as the core mesh validation
  module, building on existing `cad_rendering.py` primitives. Provide an
  `IndexedMesh` class for topology-based checks, plus individual validation
  functions and an aggregate `validate_mesh()` entry-point.
- **Rationale**: Placing the module in `src/reidce/` makes it:
  (a) importable via the installed package,
  (b) covered by mypy (`python -m mypy src`),
  (c) linted by ruff (`python -m ruff check .`),
  (d) testable via pytest in the existing `tests/` directory.
  The IndexedMesh representation enables proper edge-topology analysis that
  the existing CadMesh (which stores vertices per-face) cannot support.
- **Alternatives Rejected**:
  - *Standalone package under tools/*: Rejected because it would not be on the
    Python path and would require sys.path hacks for tests and mypy.
  - *Modify CadMesh directly*: Rejected because CadMesh is used across the
    codebase and changing its structure would be a large diff.
- **Consequences**: 25 new tests added. All 164 tests pass. The mesh validator
  integrates with existing CadMesh via `IndexedMesh.from_cad_mesh()`.

### DEC-005: CLI tool placement in tools/meshcad_assets/

- **Date**: 2026-02-12
- **Context**: Need a command-line interface for mesh validation.
- **Decision**: Place the CLI at `tools/meshcad_assets/validate_mesh.py` as a
  standalone script that imports from the installed `reidce` package.
- **Rationale**: Follows the existing pattern of `tools/validate_mathlib_v0.py`
  — standalone validation scripts in `tools/`.
- **Alternatives Rejected**:
  - *Add as sfcs-mdp subcommand*: Rejected because mesh validation is not
    a manufacturing digital thread operation.
  - *Add as pyproject.toml script entry*: Could be done later, but a standalone
    script keeps the initial diff minimal.
- **Consequences**: Users can run `python tools/meshcad_assets/validate_mesh.py
  path/to/mesh.stl` to validate any ASCII STL file.
