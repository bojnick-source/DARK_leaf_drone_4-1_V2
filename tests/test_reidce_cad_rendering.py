from reidce.cad_rendering import (
    Vec3,
    compute_cross_section,
    generate_mesh,
    mesh_quality_score,
    mesh_to_stl_text,
)
from reidce.schemas import (
    CadRef,
    GeometryKeyDimensions,
    GeometrySpec,
    GeometryTolerances,
    Quantity,
)


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


def test_generate_mesh_draft() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="draft")
    assert mesh.statistics.quality_level == "draft"
    assert mesh.statistics.vertex_count > 0
    assert mesh.statistics.triangle_count > 0
    assert mesh.statistics.edge_count > 0
    assert mesh.statistics.watertight is True


def test_generate_mesh_standard() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="standard")
    assert mesh.statistics.quality_level == "standard"
    assert mesh.statistics.vertex_count > 0
    assert mesh.statistics.triangle_count > 0


def test_generate_mesh_high_fidelity() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="high_fidelity")
    assert mesh.statistics.quality_level == "high_fidelity"
    assert mesh.statistics.vertex_count > 0
    assert mesh.statistics.triangle_count > mesh.statistics.vertex_count


def test_high_fidelity_has_more_triangles_than_draft() -> None:
    geometry = _make_geometry()
    draft = generate_mesh(geometry, quality="draft")
    hf = generate_mesh(geometry, quality="high_fidelity")
    assert hf.statistics.triangle_count > draft.statistics.triangle_count


def test_mesh_surface_area_positive() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="standard")
    assert mesh.statistics.surface_area > 0.0


def test_mesh_bounding_box() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="standard")
    bb_min = mesh.statistics.bounding_box_min
    bb_max = mesh.statistics.bounding_box_max
    assert bb_max.z > bb_min.z
    assert bb_max.x >= bb_min.x


def test_mesh_geometry_hash_deterministic() -> None:
    geometry = _make_geometry()
    mesh1 = generate_mesh(geometry, quality="standard")
    mesh2 = generate_mesh(geometry, quality="standard")
    assert mesh1.geometry_hash == mesh2.geometry_hash


def test_mesh_geometry_hash_varies_with_quality() -> None:
    geometry = _make_geometry()
    m_draft = generate_mesh(geometry, quality="draft")
    m_hf = generate_mesh(geometry, quality="high_fidelity")
    assert m_draft.geometry_hash != m_hf.geometry_hash


def test_cross_section_inside_mesh() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="standard")
    cs = compute_cross_section(mesh, z_position=0.05)
    assert cs.area > 0.0
    assert cs.perimeter > 0.0
    assert len(cs.contour_points) > 0


def test_cross_section_outside_mesh() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="standard")
    cs = compute_cross_section(mesh, z_position=999.0)
    assert cs.area == 0.0
    assert len(cs.contour_points) == 0


def test_mesh_to_stl_text() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="draft")
    stl = mesh_to_stl_text(mesh)
    assert stl.startswith("solid actuator")
    assert "endsolid actuator" in stl
    assert "facet normal" in stl
    assert "vertex" in stl


def test_mesh_quality_score() -> None:
    geometry = _make_geometry()
    mesh = generate_mesh(geometry, quality="standard")
    score = mesh_quality_score(mesh)
    assert 0.0 < score <= 1.0


def test_vec3_operations() -> None:
    a = Vec3(1.0, 0.0, 0.0)
    b = Vec3(0.0, 1.0, 0.0)
    cross = a.cross(b)
    assert abs(cross.z - 1.0) < 1e-6
    assert abs(a.dot(b)) < 1e-6
    assert abs(a.length() - 1.0) < 1e-6
