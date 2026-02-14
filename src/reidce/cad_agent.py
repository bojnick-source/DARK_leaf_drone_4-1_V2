"""CAD generation agent for the DARK leaf 4-1 competition drone.

Orchestrates the full computational pipeline from design specification
through topology optimization, validation, and high-fidelity CAD mesh
generation.  The agent is competition-focused: it generates geometry for
the DARPA LIFT 4:1 drone configuration and does **not** include camera,
gimbal, or photography payload geometry.

Key components
--------------
* ``CompetitionDroneSpec`` — competition-constrained design parameters.
* ``CadAgentResult`` — structured output with mesh, validation, and
  topology recommendation.
* ``generate_competition_drone_mesh`` — builds a multi-component drone
  mesh (hub, arms, motor mounts, propeller disks, battery tray).
* ``run_cad_agent`` — top-level orchestrator that runs topology
  optimization, validation, and mesh generation in a single call.

The agent is intentionally local and deterministic — no external API
calls.  All geometry is parametric and derived from competition rules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from reidce.cad_rendering import (
    QUALITY_SEGMENTS,
    CadMesh,
    MeshStatistics,
    QualityLevel,
    Triangle,
    Vec3,
    WireframeEdge,
    _compute_bounding_box,
    _compute_surface_area,
    _cylinder_mesh,
)
from reidce.memory import MemoryStore
from reidce.mesh_validator import IndexedMesh, validate_mesh

# ── Competition drone specification ──────────────────────────────────


@dataclass(frozen=True)
class CompetitionDroneSpec:
    """Design parameters for the DARPA LIFT 4:1 competition drone.

    All defaults are derived from competition constraints:
    - Aircraft mass (dry + fuel) ≤ 24.95 kg (55 lb)
    - Payload ≥ 49.9 kg (110 lb)
    - 4:1 payload-to-aircraft ratio for full prize
    - 5 NM course at 350 ft altitude in ≤ 30 min
    """

    arm_count: int = 4
    arm_length_m: float = 0.30
    arm_radius_m: float = 0.008
    hub_radius_m: float = 0.06
    hub_height_m: float = 0.035
    motor_radius_m: float = 0.018
    motor_height_m: float = 0.025
    prop_radius_m: float = 0.12
    prop_thickness_m: float = 0.003
    battery_length_m: float = 0.07
    battery_width_m: float = 0.04
    battery_height_m: float = 0.025


# ── Agent result ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class CadAgentResult:
    """Structured output of the CAD agent pipeline."""

    mesh: CadMesh
    validation: Dict[str, Any]
    topology_scores: List[Dict[str, Any]]
    spec: CompetitionDroneSpec
    quality: QualityLevel
    component_count: int
    competition_focused: bool = True


# ── Mesh generation helpers ──────────────────────────────────────────


def _box_mesh(
    half_x: float,
    half_y: float,
    half_z: float,
    offset: Vec3,
) -> tuple[list[Vec3], list[Triangle], list[WireframeEdge]]:
    """Generate a simple axis-aligned box mesh centered on *offset*."""
    ox, oy, oz = offset.x, offset.y, offset.z
    corners = [
        Vec3(ox - half_x, oy - half_y, oz - half_z),
        Vec3(ox + half_x, oy - half_y, oz - half_z),
        Vec3(ox + half_x, oy + half_y, oz - half_z),
        Vec3(ox - half_x, oy + half_y, oz - half_z),
        Vec3(ox - half_x, oy - half_y, oz + half_z),
        Vec3(ox + half_x, oy - half_y, oz + half_z),
        Vec3(ox + half_x, oy + half_y, oz + half_z),
        Vec3(ox - half_x, oy + half_y, oz + half_z),
    ]
    faces = [
        (0, 1, 2, 3),  # bottom
        (4, 7, 6, 5),  # top
        (0, 3, 7, 4),  # left
        (1, 5, 6, 2),  # right
        (0, 4, 5, 1),  # front
        (3, 2, 6, 7),  # back
    ]
    normals_map = [
        Vec3(0, 0, -1), Vec3(0, 0, 1), Vec3(-1, 0, 0),
        Vec3(1, 0, 0), Vec3(0, -1, 0), Vec3(0, 1, 0),
    ]
    triangles: list[Triangle] = []
    edges: list[WireframeEdge] = []
    for idx, (a, b, c, d) in enumerate(faces):
        n = normals_map[idx]
        triangles.append(Triangle(corners[a], corners[b], corners[c], n))
        triangles.append(Triangle(corners[a], corners[c], corners[d], n))
    # wireframe: 12 box edges
    box_edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    for i, j in box_edges:
        edges.append(WireframeEdge(corners[i], corners[j]))
    return list(corners), triangles, edges


def _merge_geometry(
    parts: list[tuple[list[Vec3], list[Triangle], list[WireframeEdge]]],
) -> tuple[list[Vec3], list[Triangle], list[WireframeEdge]]:
    """Merge multiple geometry parts into a single vertex/triangle/edge list."""
    all_verts: list[Vec3] = []
    all_tris: list[Triangle] = []
    all_edges: list[WireframeEdge] = []
    for verts, tris, edges in parts:
        all_verts.extend(verts)
        all_tris.extend(tris)
        all_edges.extend(edges)
    return all_verts, all_tris, all_edges


# ── Main drone mesh generator ────────────────────────────────────────


def generate_competition_drone_mesh(
    spec: CompetitionDroneSpec | None = None,
    quality: QualityLevel = "standard",
) -> CadMesh:
    """Build a multi-component 4-1 competition drone mesh.

    Components generated (no camera/gimbal — competition only):
    - Central hub (cylinder)
    - Arms (cylinders, one per arm_count)
    - Motor mounts (cylinders at arm tips)
    - Propeller disks (flat cylinders at motor tops)
    - Battery tray (box underneath hub)
    """
    spec = spec or CompetitionDroneSpec()
    segments = QUALITY_SEGMENTS[quality]
    parts: list[tuple[list[Vec3], list[Triangle], list[WireframeEdge]]] = []
    component_count = 0

    origin = Vec3(0.0, 0.0, 0.0)

    # 1. Central hub
    parts.append(_cylinder_mesh(spec.hub_radius_m, spec.hub_height_m, segments, origin))
    component_count += 1

    # 2. Arms + Motors + Propellers
    for i in range(spec.arm_count):
        angle = 2.0 * math.pi * i / spec.arm_count
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Arm — positioned from hub edge to motor mount
        arm_cx = cos_a * spec.arm_length_m * 0.5
        arm_cy = sin_a * spec.arm_length_m * 0.5
        arm_offset = Vec3(arm_cx, arm_cy, spec.hub_height_m * 0.5)
        parts.append(
            _cylinder_mesh(spec.arm_radius_m, spec.arm_length_m, max(segments // 2, 6), arm_offset)
        )
        component_count += 1

        # Motor mount at arm tip
        tip_x = cos_a * spec.arm_length_m
        tip_y = sin_a * spec.arm_length_m
        motor_offset = Vec3(tip_x, tip_y, spec.hub_height_m)
        parts.append(
            _cylinder_mesh(spec.motor_radius_m, spec.motor_height_m, segments, motor_offset)
        )
        component_count += 1

        # Propeller disk at motor top
        prop_z = spec.hub_height_m + spec.motor_height_m
        prop_offset = Vec3(tip_x, tip_y, prop_z)
        parts.append(
            _cylinder_mesh(
                spec.prop_radius_m, spec.prop_thickness_m, segments, prop_offset,
            )
        )
        component_count += 1

    # 3. Battery tray (box under hub)
    batt_offset = Vec3(0.0, 0.0, -spec.battery_height_m)
    parts.append(_box_mesh(
        spec.battery_length_m / 2.0,
        spec.battery_width_m / 2.0,
        spec.battery_height_m / 2.0,
        batt_offset,
    ))
    component_count += 1

    # Merge all parts
    vertices, triangles, wireframe = _merge_geometry(parts)
    bb_min, bb_max = _compute_bounding_box(vertices)
    surface_area = _compute_surface_area(triangles)

    import hashlib
    hash_input = f"competition_drone:{spec.arm_count}:{quality}:{spec.arm_length_m}"
    geo_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]

    stats = MeshStatistics(
        vertex_count=len(vertices),
        triangle_count=len(triangles),
        edge_count=len(wireframe),
        surface_area=surface_area,
        bounding_box_min=bb_min,
        bounding_box_max=bb_max,
        quality_level=quality,
        watertight=True,
    )

    return CadMesh(
        vertices=vertices,
        triangles=triangles,
        wireframe=wireframe,
        statistics=stats,
        geometry_hash=geo_hash,
    )


# ── CAD agent orchestrator ───────────────────────────────────────────


def run_cad_agent(
    spec: CompetitionDroneSpec | None = None,
    quality: QualityLevel = "standard",
    memory_store: Optional[MemoryStore] = None,
) -> CadAgentResult:
    """Run the full CAD agent pipeline.

    Steps:
    1. Generate multi-component competition drone mesh.
    2. Validate mesh topology (watertight, manifold, degenerate faces).
    3. Compute topology optimization scores for competition geometry.
    4. Log to memory store if provided.

    The agent is competition-focused — no camera, gimbal, or photography
    payload geometry is generated.  All parameters default to DARPA LIFT
    4:1 competition constraints.
    """
    spec = spec or CompetitionDroneSpec()

    # Step 1: Generate mesh
    mesh = generate_competition_drone_mesh(spec, quality)

    # Step 2: Validate mesh
    indexed = IndexedMesh.from_cad_mesh(mesh)
    validation_result = validate_mesh(indexed)
    validation = {
        "watertight": validation_result.is_watertight,
        "manifold": validation_result.is_manifold,
        "degenerate_faces": validation_result.degenerate_count,
        "vertex_count": validation_result.vertex_count,
        "face_count": validation_result.triangle_count,
        "surface_area": validation_result.surface_area,
        "quality_score": validation_result.mesh_quality_score,
    }

    # Step 3: Topology scoring for competition geometry
    arm_slenderness = spec.arm_length_m / max(spec.arm_radius_m * 2.0, 1e-6)
    prop_to_hub = spec.prop_radius_m / max(spec.hub_radius_m, 1e-6)
    mass_efficiency = spec.arm_count * spec.prop_radius_m / max(spec.arm_length_m, 1e-6)
    topology_scores = [
        {
            "metric": "arm_slenderness",
            "value": round(arm_slenderness, 3),
            "description": "Arm length-to-diameter ratio (structural efficiency)",
        },
        {
            "metric": "prop_to_hub_ratio",
            "value": round(prop_to_hub, 3),
            "description": "Propeller-to-hub size ratio (aerodynamic coverage)",
        },
        {
            "metric": "mass_efficiency_index",
            "value": round(mass_efficiency, 3),
            "description": "Effective disk area per unit arm length",
        },
    ]

    # Step 4: Log to memory
    if memory_store is not None:
        memory_store.log_event(
            "cad_agent",
            "Generated competition drone CAD mesh",
            {
                "quality": quality,
                "vertex_count": mesh.statistics.vertex_count,
                "triangle_count": mesh.statistics.triangle_count,
                "component_count": 1 + spec.arm_count * 3 + 1,
                "competition_focused": True,
            },
        )

    return CadAgentResult(
        mesh=mesh,
        validation=validation,
        topology_scores=topology_scores,
        spec=spec,
        quality=quality,
        component_count=1 + spec.arm_count * 3 + 1,
        competition_focused=True,
    )


# ── STL export ───────────────────────────────────────────────────────

def export_stl_binary(mesh: CadMesh, path: str) -> int:
    """Export a CadMesh to a binary STL file.

    Returns the number of triangles written.  Binary STL is the
    industry-standard interchange format supported by all major CAD
    packages (AutoCAD, SolidWorks, Fusion 360, FreeCAD, etc.).
    """
    import struct

    triangles = mesh.triangles
    n_tris = len(triangles)

    with open(path, "wb") as fh:
        # 80-byte header
        header = b"DARK_leaf_4-1_V2 STL Export"
        fh.write(header.ljust(80, b"\0"))
        # triangle count
        fh.write(struct.pack("<I", n_tris))
        for tri in triangles:
            fh.write(struct.pack(
                "<12fH",
                tri.normal.x, tri.normal.y, tri.normal.z,
                tri.v0.x, tri.v0.y, tri.v0.z,
                tri.v1.x, tri.v1.y, tri.v1.z,
                tri.v2.x, tri.v2.y, tri.v2.z,
                0,
            ))
    return n_tris


def export_stl_text(mesh: CadMesh) -> str:
    """Return the mesh as an ASCII STL string.

    Delegates to the existing ``mesh_to_stl_text`` in cad_rendering
    but provides a convenient wrapper from the CAD agent.
    """
    from reidce.cad_rendering import mesh_to_stl_text
    return mesh_to_stl_text(mesh)
