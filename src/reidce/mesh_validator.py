"""Mesh validation and quality analysis for drone component meshes.

Provides indexed-mesh conversion, topology checks (watertight, manifold,
degenerate-face detection), normal-consistency verification, and an
aggregate ``validate_mesh`` entry-point that produces a structured
``ValidationResult``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from reidce.cad_rendering import CadMesh, Vec3

# ---------------------------------------------------------------------------
# Indexed mesh representation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IndexedMesh:
    """Triangle mesh stored as vertex positions + face index triples.

    This is the canonical representation for topology-based validation.
    Vertices are de-duplicated with a configurable tolerance.
    """

    vertices: List[Tuple[float, float, float]]
    faces: List[Tuple[int, int, int]]

    # -- factories ----------------------------------------------------------

    @classmethod
    def from_cad_mesh(cls, mesh: CadMesh, tolerance: int = 10) -> IndexedMesh:
        """Build an ``IndexedMesh`` from a ``CadMesh``.

        *tolerance* is the number of decimal places used when rounding
        vertex positions for de-duplication.
        """
        vertex_map: Dict[Tuple[float, float, float], int] = {}
        vertices: List[Tuple[float, float, float]] = []
        faces: List[Tuple[int, int, int]] = []

        def _get_or_add(v: Vec3) -> int:
            key = (round(v.x, tolerance), round(v.y, tolerance), round(v.z, tolerance))
            idx = vertex_map.get(key)
            if idx is None:
                idx = len(vertices)
                vertex_map[key] = idx
                vertices.append(key)
            return idx

        for tri in mesh.triangles:
            i0 = _get_or_add(tri.v0)
            i1 = _get_or_add(tri.v1)
            i2 = _get_or_add(tri.v2)
            faces.append((i0, i1, i2))

        return cls(vertices=vertices, faces=faces)

    @classmethod
    def from_stl_text(cls, text: str, tolerance: int = 10) -> IndexedMesh:
        """Parse an ASCII STL string and return an ``IndexedMesh``."""
        vertex_map: Dict[Tuple[float, float, float], int] = {}
        vertices: List[Tuple[float, float, float]] = []
        faces: List[Tuple[int, int, int]] = []
        current_face_verts: List[int] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.startswith("vertex"):
                parts = line.split()
                if len(parts) < 4:
                    continue
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                key = (round(x, tolerance), round(y, tolerance), round(z, tolerance))
                idx = vertex_map.get(key)
                if idx is None:
                    idx = len(vertices)
                    vertex_map[key] = idx
                    vertices.append(key)
                current_face_verts.append(idx)
            elif line == "endloop":
                if len(current_face_verts) == 3:
                    faces.append(tuple(current_face_verts))  # type: ignore[arg-type]
                current_face_verts = []

        return cls(vertices=vertices, faces=faces)


# ---------------------------------------------------------------------------
# Edge helpers
# ---------------------------------------------------------------------------

def _edge_key(v0: int, v1: int) -> Tuple[int, int]:
    """Return a canonical (sorted) edge key."""
    return (v0, v1) if v0 <= v1 else (v1, v0)


def _build_edge_face_map(
    faces: Sequence[Tuple[int, int, int]],
) -> Dict[Tuple[int, int], List[int]]:
    """Map each undirected edge to the indices of faces that share it."""
    edge_faces: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for fi, (a, b, c) in enumerate(faces):
        edge_faces[_edge_key(a, b)].append(fi)
        edge_faces[_edge_key(b, c)].append(fi)
        edge_faces[_edge_key(c, a)].append(fi)
    return dict(edge_faces)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def find_degenerate_faces(
    mesh: IndexedMesh,
    area_threshold: float = 1e-12,
) -> List[int]:
    """Return indices of triangles whose area is below *area_threshold*."""
    degenerate: List[int] = []
    for fi, (i0, i1, i2) in enumerate(mesh.faces):
        v0 = Vec3(*mesh.vertices[i0])
        v1 = Vec3(*mesh.vertices[i1])
        v2 = Vec3(*mesh.vertices[i2])
        edge1 = v1.sub(v0)
        edge2 = v2.sub(v0)
        area = 0.5 * edge1.cross(edge2).length()
        if area < area_threshold:
            degenerate.append(fi)
    return degenerate


def check_watertight(mesh: IndexedMesh) -> Tuple[bool, int]:
    """Return ``(is_watertight, boundary_edge_count)``.

    A mesh is *watertight* when every edge is shared by exactly two faces
    (no boundary edges).
    """
    edge_map = _build_edge_face_map(mesh.faces)
    boundary = sum(1 for face_list in edge_map.values() if len(face_list) != 2)
    return boundary == 0, boundary


def check_manifold(mesh: IndexedMesh) -> Tuple[bool, int]:
    """Return ``(is_manifold, non_manifold_edge_count)``.

    A mesh is *2-manifold* when every edge is shared by at most two faces.
    """
    edge_map = _build_edge_face_map(mesh.faces)
    non_manifold = sum(1 for face_list in edge_map.values() if len(face_list) > 2)
    return non_manifold == 0, non_manifold


def compute_face_normals(mesh: IndexedMesh) -> List[Vec3]:
    """Return one unit-length normal per face via the cross-product rule."""
    normals: List[Vec3] = []
    for i0, i1, i2 in mesh.faces:
        v0 = Vec3(*mesh.vertices[i0])
        v1 = Vec3(*mesh.vertices[i1])
        v2 = Vec3(*mesh.vertices[i2])
        edge1 = v1.sub(v0)
        edge2 = v2.sub(v0)
        normals.append(edge1.cross(edge2).normalized())
    return normals


def compute_vertex_normals(mesh: IndexedMesh) -> List[Vec3]:
    """Compute smooth (area-weighted, averaged) vertex normals."""
    accum: List[List[float]] = [[0.0, 0.0, 0.0] for _ in mesh.vertices]

    for i0, i1, i2 in mesh.faces:
        v0 = Vec3(*mesh.vertices[i0])
        v1 = Vec3(*mesh.vertices[i1])
        v2 = Vec3(*mesh.vertices[i2])
        edge1 = v1.sub(v0)
        edge2 = v2.sub(v0)
        cross = edge1.cross(edge2)
        for idx in (i0, i1, i2):
            accum[idx][0] += cross.x
            accum[idx][1] += cross.y
            accum[idx][2] += cross.z

    result: List[Vec3] = []
    for a in accum:
        v = Vec3(a[0], a[1], a[2])
        result.append(v.normalized())
    return result


def check_normals_consistent(mesh: IndexedMesh) -> bool:
    """Check that adjacent faces have consistently oriented normals.

    Two faces sharing an edge should induce *opposite* vertex orderings
    on that shared edge.  If any shared edge has the same winding in
    both faces the normals are inconsistent.
    """
    # Build a directed-edge → face map.
    directed: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for fi, (a, b, c) in enumerate(mesh.faces):
        directed[(a, b)].append(fi)
        directed[(b, c)].append(fi)
        directed[(c, a)].append(fi)

    for (_u, _v), face_list in directed.items():
        if len(face_list) > 1:
            # Same directed edge used by more than one face → inconsistent
            return False
    return True


def compute_surface_area(mesh: IndexedMesh) -> float:
    """Return the total surface area of *mesh*."""
    total = 0.0
    for i0, i1, i2 in mesh.faces:
        v0 = Vec3(*mesh.vertices[i0])
        v1 = Vec3(*mesh.vertices[i1])
        v2 = Vec3(*mesh.vertices[i2])
        edge1 = v1.sub(v0)
        edge2 = v2.sub(v0)
        total += 0.5 * edge1.cross(edge2).length()
    return total


def compute_mesh_quality_score(mesh: IndexedMesh) -> float:
    """Return a quality score in [0, 1] based on triangle aspect ratios.

    A score of 1.0 means all triangles are equilateral; lower values
    indicate degenerate triangles.
    """
    if not mesh.faces:
        return 0.0
    scores: List[float] = []
    for i0, i1, i2 in mesh.faces:
        v0 = Vec3(*mesh.vertices[i0])
        v1 = Vec3(*mesh.vertices[i1])
        v2 = Vec3(*mesh.vertices[i2])
        a = v1.sub(v0).length()
        b = v2.sub(v1).length()
        c = v0.sub(v2).length()
        longest = max(a, b, c)
        if longest < 1e-12:
            scores.append(0.0)
            continue
        shortest = min(a, b, c)
        scores.append(shortest / longest)
    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Aggregate result
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Aggregate result of all mesh validation checks."""

    is_watertight: bool
    is_manifold: bool
    degenerate_count: int
    degenerate_indices: List[int]
    vertex_count: int
    triangle_count: int
    edge_count: int
    boundary_edge_count: int
    non_manifold_edge_count: int
    surface_area: float
    mesh_quality_score: float
    normals_consistent: bool

    @property
    def is_valid(self) -> bool:
        """``True`` when the mesh passes all topology checks."""
        return (
            self.is_watertight
            and self.is_manifold
            and self.degenerate_count == 0
            and self.normals_consistent
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "is_valid": self.is_valid,
            "is_watertight": self.is_watertight,
            "is_manifold": self.is_manifold,
            "normals_consistent": self.normals_consistent,
            "degenerate_count": self.degenerate_count,
            "degenerate_indices": self.degenerate_indices,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "edge_count": self.edge_count,
            "boundary_edge_count": self.boundary_edge_count,
            "non_manifold_edge_count": self.non_manifold_edge_count,
            "surface_area": self.surface_area,
            "mesh_quality_score": self.mesh_quality_score,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

def validate_mesh(mesh: IndexedMesh) -> ValidationResult:
    """Run all validation checks on *mesh* and return a ``ValidationResult``."""
    degenerate = find_degenerate_faces(mesh)
    is_watertight, boundary_edges = check_watertight(mesh)
    is_manifold, non_manifold_edges = check_manifold(mesh)
    normals_ok = check_normals_consistent(mesh)
    area = compute_surface_area(mesh)
    quality = compute_mesh_quality_score(mesh)
    edge_map = _build_edge_face_map(mesh.faces)

    return ValidationResult(
        is_watertight=is_watertight,
        is_manifold=is_manifold,
        degenerate_count=len(degenerate),
        degenerate_indices=degenerate,
        vertex_count=len(mesh.vertices),
        triangle_count=len(mesh.faces),
        edge_count=len(edge_map),
        boundary_edge_count=boundary_edges,
        non_manifold_edge_count=non_manifold_edges,
        surface_area=area,
        mesh_quality_score=quality,
        normals_consistent=normals_ok,
    )
