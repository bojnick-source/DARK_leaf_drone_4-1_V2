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

## Mesh Validation Requirements

| Req ID | Requirement | Implementation | Test | Evidence | Status |
|--------|-------------|----------------|------|----------|--------|
| MESH-01 | Watertight check: detect boundary edges | `src/reidce/mesh_validator.py::check_watertight` | `tests/test_mesh_validator.py::TestWatertight` | 3 tests pass | PASS |
| MESH-02 | Manifold check: detect non-manifold edges | `src/reidce/mesh_validator.py::check_manifold` | `tests/test_mesh_validator.py::TestManifold` | 2 tests pass | PASS |
| MESH-03 | Degenerate face detection: zero-area triangles | `src/reidce/mesh_validator.py::find_degenerate_faces` | `tests/test_mesh_validator.py::TestDegenerateFaces` | 3 tests pass | PASS |
| MESH-04 | Face normal computation | `src/reidce/mesh_validator.py::compute_face_normals` | `tests/test_mesh_validator.py::TestNormals::test_face_normals_unit_length` | Unit-length normals verified | PASS |
| MESH-05 | Vertex normal computation (area-weighted) | `src/reidce/mesh_validator.py::compute_vertex_normals` | `tests/test_mesh_validator.py::TestNormals::test_vertex_normals_unit_length` | Unit-length normals verified | PASS |
| MESH-06 | Normal consistency check | `src/reidce/mesh_validator.py::check_normals_consistent` | `tests/test_mesh_validator.py::TestNormals` | Consistent and inconsistent cases tested | PASS |
| MESH-07 | Surface area computation | `src/reidce/mesh_validator.py::compute_surface_area` | `tests/test_mesh_validator.py::TestSurfaceAreaAndQuality` | Positive area verified | PASS |
| MESH-08 | Mesh quality score (aspect ratio) | `src/reidce/mesh_validator.py::compute_mesh_quality_score` | `tests/test_mesh_validator.py::TestSurfaceAreaAndQuality` | Score in [0, 1] verified | PASS |
| MESH-09 | Aggregate `validate_mesh()` entry-point | `src/reidce/mesh_validator.py::validate_mesh` | `tests/test_mesh_validator.py::TestValidateMesh` | 5 tests pass | PASS |
| MESH-10 | JSON report output | `src/reidce/mesh_validator.py::ValidationResult.to_json` | `tests/test_mesh_validator.py::TestValidateMesh::test_result_json_roundtrip` | JSON roundtrip verified | PASS |
| MESH-11 | STL parser (ASCII) | `src/reidce/mesh_validator.py::IndexedMesh.from_stl_text` | `tests/test_mesh_validator.py::TestIndexedMeshFromStl` | 2 tests pass | PASS |
| MESH-12 | CadMesh → IndexedMesh conversion | `src/reidce/mesh_validator.py::IndexedMesh.from_cad_mesh` | `tests/test_mesh_validator.py::TestIndexedMeshFromCadMesh` | 2 tests pass | PASS |
| MESH-13 | STL roundtrip: generate → export → parse → validate | `src/reidce/mesh_validator.py` + `src/reidce/cad_rendering.py` | `tests/test_mesh_validator.py::TestStlRoundTrip` | Triangle count preserved | PASS |
| MESH-14 | CLI tool for mesh validation | `tools/meshcad_assets/validate_mesh.py` | Manual CLI test | Exit codes 0/1/2 verified | PASS |

## Core Principles

| Req ID | Requirement | Implementation | Test | Evidence | Status |
|--------|-------------|----------------|------|----------|--------|
| CORE-01 | Explicit → Verified → Logged | `tools/meshcad_assets/docs/TRACEABILITY.md` | Manual review | This document | PASS |
| CORE-02 | No silent guessing | `src/sfcs_mdp/validate.py`, `src/sfcs_mdp/model.py` | `python -m pytest` | 164 tests pass | PASS |
| CORE-03 | Plan-then-execute with gated milestones | `tools/meshcad_assets/docs/DECISIONS.md` | Manual review | Decision log maintained | PASS |
| CORE-04 | Self-check loops | CI pipeline (`.github/workflows/ci.yml`) | Full CI suite | ruff + mypy + pytest + mathlib all green | PASS |
| CORE-05 | Determinism enforcement | `pyproject.toml` (pinned deps) | `pip install .[dev]` | Exact versions pinned | PASS |
| CORE-06 | Minimal, reviewable diffs | PR review process | `git diff --stat` | Small commits per milestone | PASS |
| CORE-07 | Security: default offline | Satisfied by design: no network functionality | `grep -r "requests\|urllib\|http" src/` | No network calls in codebase | PASS |
| DOC-01 | TRACEABILITY.md exists | `tools/meshcad_assets/docs/TRACEABILITY.md` | `test -f` | File exists | PASS |
| DOC-02 | DECISIONS.md exists | `tools/meshcad_assets/docs/DECISIONS.md` | `test -f` | File exists | PASS |

## Notes

- 25 new unit tests added in `tests/test_mesh_validator.py`
- All 164 tests pass (139 existing + 25 new)
- All CI gates remain green (ruff, mypy, pytest, mathlib validation)
