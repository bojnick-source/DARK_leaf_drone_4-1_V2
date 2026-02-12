"""Tests for reidce.mesh_validator — topology checks and quality metrics."""

from __future__ import annotations

import json
import math

from reidce.cad_rendering import (
    generate_mesh,
    mesh_to_stl_text,
)
from reidce.mesh_validator import (
    IndexedMesh,
    check_manifold,
    check_normals_consistent,
    check_watertight,
    compute_face_normals,
    compute_mesh_quality_score,
    compute_surface_area,
    compute_vertex_normals,
    find_degenerate_faces,
    validate_mesh,
)
from reidce.schemas import (
    CadRef,
    GeometryKeyDimensions,
    GeometrySpec,
    GeometryTolerances,
    Quantity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quantity(value: float, unit: str) -> Quantity:
    return Quantity(value=value, unit=unit)


def _make_geometry() -> GeometrySpec:
    return GeometrySpec(
        schema_version="geometry.v1.0",
        cad_ref=CadRef(type="none", uri=None, sha256=None),
        envelope_max=_quantity(0.2, "m"),
        key_dimensions=GeometryKeyDimensions(
            actuator_diameter=_quantity(0.02, "m"),
            actuator_wall_thickness=_quantity(0.001, "m"),
            actuator_length=_quantity(0.1, "m"),
        ),
        tolerances=GeometryTolerances(
            general_linear=_quantity(0.0001, "m"),
            critical_linear=_quantity(0.00005, "m"),
            critical_features=[],
        ),
    )


def _make_tetrahedron() -> IndexedMesh:
    """Create a closed tetrahedron (4 faces, 4 vertices, watertight)."""
    vertices = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.5, math.sqrt(3) / 2, 0.0),
        (0.5, math.sqrt(3) / 6, math.sqrt(6) / 3),
    ]
    # Faces wound so that normals point outward.
    faces = [
        (0, 2, 1),
        (0, 1, 3),
        (1, 2, 3),
        (0, 3, 2),
    ]
    return IndexedMesh(vertices=vertices, faces=faces)


def _make_open_triangle() -> IndexedMesh:
    """Single triangle — not watertight, but manifold."""
    vertices = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.5, 1.0, 0.0),
    ]
    faces = [(0, 1, 2)]
    return IndexedMesh(vertices=vertices, faces=faces)


# ---------------------------------------------------------------------------
# IndexedMesh construction
# ---------------------------------------------------------------------------

class TestIndexedMeshFromCadMesh:
    def test_roundtrip_preserves_face_count(self) -> None:
        geometry = _make_geometry()
        cad_mesh = generate_mesh(geometry, quality="draft")
        indexed = IndexedMesh.from_cad_mesh(cad_mesh)
        assert len(indexed.faces) == cad_mesh.statistics.triangle_count

    def test_vertices_are_deduplicated(self) -> None:
        geometry = _make_geometry()
        cad_mesh = generate_mesh(geometry, quality="draft")
        indexed = IndexedMesh.from_cad_mesh(cad_mesh)
        # The indexed mesh should have fewer unique vertices than the raw
        # CadMesh vertex list (which stores 3 verts per triangle).
        assert len(indexed.vertices) <= len(cad_mesh.vertices)


class TestIndexedMeshFromStl:
    def test_stl_roundtrip(self) -> None:
        geometry = _make_geometry()
        cad_mesh = generate_mesh(geometry, quality="draft")
        stl_text = mesh_to_stl_text(cad_mesh)
        indexed = IndexedMesh.from_stl_text(stl_text)
        assert len(indexed.faces) == cad_mesh.statistics.triangle_count

    def test_empty_stl(self) -> None:
        indexed = IndexedMesh.from_stl_text("")
        assert len(indexed.faces) == 0
        assert len(indexed.vertices) == 0


# ---------------------------------------------------------------------------
# Watertight check
# ---------------------------------------------------------------------------

class TestWatertight:
    def test_closed_tetrahedron_is_watertight(self) -> None:
        mesh = _make_tetrahedron()
        is_wt, boundary = check_watertight(mesh)
        assert is_wt is True
        assert boundary == 0

    def test_single_triangle_is_not_watertight(self) -> None:
        mesh = _make_open_triangle()
        is_wt, boundary = check_watertight(mesh)
        assert is_wt is False
        assert boundary > 0

    def test_cad_mesh_cylinder_is_watertight(self) -> None:
        geometry = _make_geometry()
        cad_mesh = generate_mesh(geometry, quality="standard")
        indexed = IndexedMesh.from_cad_mesh(cad_mesh)
        is_wt, _ = check_watertight(indexed)
        assert is_wt is True


# ---------------------------------------------------------------------------
# Manifold check
# ---------------------------------------------------------------------------

class TestManifold:
    def test_tetrahedron_is_manifold(self) -> None:
        mesh = _make_tetrahedron()
        is_mf, nm = check_manifold(mesh)
        assert is_mf is True
        assert nm == 0

    def test_non_manifold_edge(self) -> None:
        """Three faces sharing the same edge → non-manifold."""
        verts = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.5, 1.0, 0.0),
            (0.5, -1.0, 0.0),
            (0.5, 0.0, 1.0),
        ]
        faces = [
            (0, 1, 2),
            (0, 1, 3),
            (0, 1, 4),
        ]
        mesh = IndexedMesh(vertices=verts, faces=faces)
        is_mf, nm = check_manifold(mesh)
        assert is_mf is False
        assert nm > 0


# ---------------------------------------------------------------------------
# Degenerate faces
# ---------------------------------------------------------------------------

class TestDegenerateFaces:
    def test_tetrahedron_has_no_degenerates(self) -> None:
        mesh = _make_tetrahedron()
        degens = find_degenerate_faces(mesh)
        assert degens == []

    def test_zero_area_triangle_detected(self) -> None:
        """Three collinear points → degenerate triangle."""
        verts = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (2.0, 0.0, 0.0),
        ]
        mesh = IndexedMesh(vertices=verts, faces=[(0, 1, 2)])
        degens = find_degenerate_faces(mesh)
        assert degens == [0]

    def test_duplicate_vertices_detected(self) -> None:
        verts = [
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
        ]
        mesh = IndexedMesh(vertices=verts, faces=[(0, 1, 2)])
        degens = find_degenerate_faces(mesh)
        assert degens == [0]


# ---------------------------------------------------------------------------
# Normals
# ---------------------------------------------------------------------------

class TestNormals:
    def test_face_normals_unit_length(self) -> None:
        mesh = _make_tetrahedron()
        normals = compute_face_normals(mesh)
        assert len(normals) == len(mesh.faces)
        for n in normals:
            assert abs(n.length() - 1.0) < 1e-6

    def test_vertex_normals_unit_length(self) -> None:
        mesh = _make_tetrahedron()
        normals = compute_vertex_normals(mesh)
        assert len(normals) == len(mesh.vertices)
        for n in normals:
            assert abs(n.length() - 1.0) < 1e-6

    def test_consistent_normals_on_tetrahedron(self) -> None:
        mesh = _make_tetrahedron()
        assert check_normals_consistent(mesh) is True

    def test_inconsistent_normals_detected(self) -> None:
        """Flip one face to make normals inconsistent."""
        verts = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.5, 1.0, 0.0),
            (0.5, 0.0, 1.0),
        ]
        faces = [
            (0, 1, 2),
            (0, 1, 3),  # same edge (0,1) wound in the same direction
        ]
        mesh = IndexedMesh(vertices=verts, faces=faces)
        assert check_normals_consistent(mesh) is False


# ---------------------------------------------------------------------------
# Surface area & quality score
# ---------------------------------------------------------------------------

class TestSurfaceAreaAndQuality:
    def test_surface_area_positive(self) -> None:
        mesh = _make_tetrahedron()
        area = compute_surface_area(mesh)
        assert area > 0.0

    def test_quality_score_bounded(self) -> None:
        mesh = _make_tetrahedron()
        score = compute_mesh_quality_score(mesh)
        assert 0.0 < score <= 1.0

    def test_empty_mesh_quality_zero(self) -> None:
        mesh = IndexedMesh(vertices=[], faces=[])
        assert compute_mesh_quality_score(mesh) == 0.0


# ---------------------------------------------------------------------------
# validate_mesh (aggregate)
# ---------------------------------------------------------------------------

class TestValidateMesh:
    def test_tetrahedron_valid(self) -> None:
        mesh = _make_tetrahedron()
        result = validate_mesh(mesh)
        assert result.is_valid is True
        assert result.is_watertight is True
        assert result.is_manifold is True
        assert result.normals_consistent is True
        assert result.degenerate_count == 0
        assert result.vertex_count == 4
        assert result.triangle_count == 4

    def test_open_mesh_invalid(self) -> None:
        mesh = _make_open_triangle()
        result = validate_mesh(mesh)
        assert result.is_valid is False
        assert result.is_watertight is False

    def test_cad_mesh_cylinder_validates(self) -> None:
        geometry = _make_geometry()
        cad_mesh = generate_mesh(geometry, quality="standard")
        indexed = IndexedMesh.from_cad_mesh(cad_mesh)
        result = validate_mesh(indexed)
        assert result.vertex_count > 0
        assert result.triangle_count > 0
        assert result.surface_area > 0.0

    def test_result_json_roundtrip(self) -> None:
        mesh = _make_tetrahedron()
        result = validate_mesh(mesh)
        data = json.loads(result.to_json())
        assert data["is_valid"] is True
        assert data["vertex_count"] == 4
        assert data["triangle_count"] == 4
        assert isinstance(data["surface_area"], float)

    def test_result_to_dict(self) -> None:
        mesh = _make_tetrahedron()
        result = validate_mesh(mesh)
        d = result.to_dict()
        assert set(d.keys()) == {
            "is_valid",
            "is_watertight",
            "is_manifold",
            "normals_consistent",
            "degenerate_count",
            "degenerate_indices",
            "vertex_count",
            "triangle_count",
            "edge_count",
            "boundary_edge_count",
            "non_manifold_edge_count",
            "surface_area",
            "mesh_quality_score",
        }


# ---------------------------------------------------------------------------
# STL round-trip via CadMesh
# ---------------------------------------------------------------------------

class TestStlRoundTrip:
    def test_generate_then_validate(self) -> None:
        """Generate a CadMesh, export to STL, parse back, validate."""
        geometry = _make_geometry()
        cad_mesh = generate_mesh(geometry, quality="draft")
        stl_text = mesh_to_stl_text(cad_mesh)
        indexed = IndexedMesh.from_stl_text(stl_text)
        result = validate_mesh(indexed)
        assert result.triangle_count == cad_mesh.statistics.triangle_count
        assert result.surface_area > 0.0
